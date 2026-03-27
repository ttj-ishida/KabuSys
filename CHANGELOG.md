# CHANGELOG

このプロジェクトは Keep a Changelog のフォーマットに従って管理しています。  
すべての公開変更はここに記録されます。

全体方針: 主要な機能追加・変更・修正のみを記載しています。実装上の設計方針（ルックアヘッドバイアス防止、フェイルセーフ、冪等性など）は各モジュールのドキュメントに記載されています。

## [0.1.0] - 2026-03-27
初回公開リリース。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージ初期化（src/kabusys/__init__.py）とバージョン指定（0.1.0）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 行の堅牢なパーサを実装（コメント、export プレフィックス、シングル/ダブルクォーテーション、バックスラッシュエスケープ対応）。
  - 上書き時に OS 環境変数を保護する protected 機能。
  - Settings クラスで主要設定をプロパティとして公開（J-Quants, kabuステーション, Slack, DB パス, 環境 / ログレベルなど）。
  - 設定バリデーション（env の許容値、LOG_LEVEL の検証）と is_live / is_paper / is_dev の便宜プロパティ。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode でセンチメント評価を行い ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（JST基準 → UTC変換）のユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数のトリム、レスポンスの厳密なバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。失敗はスキップして継続（フェイルセーフ）。
    - レスポンス JSON の復元処理（前後に余計なテキストが混ざる場合の {} 抽出）、スコアの ±1.0 クリップ。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を計算、calc_news_window に基づくニュース抽出、OpenAI 呼び出しとリトライ、最終的に market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI API 呼出し失敗時のフォールバック（macro_sentiment=0.0）を採用。

- データ処理（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を使った営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - JPX カレンダー差分取得の夜間バッチ calendar_update_job（J-Quants からの差分取得・バックフィル・健全性チェック）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - 差分取得、保存（jquants_client の save_* を用いた冪等保存）、品質チェック連携を行う設計方針を実装の基礎として定義。
    - data.etl で ETLResult を再エクスポート。

- リサーチ機能（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、ATR 比、出来高比等）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials を元に計算する関数群を実装。
    - データ不足時は None を返す設計、返却は (date, code) をキーとする dict のリスト。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で完結する実装。

- モジュールエクスポート
  - ai.__init__.py, research.__init__.py で主要関数を公開。

### 変更点（設計上の重要事項）
- ルックアヘッドバイアス回避:
  - AI / リサーチ / ETL 系のモジュールは内部で datetime.today() / date.today() を参照しないよう留意し、target_date を明示的に受け取る設計。データクエリも target_date 未満/以前の条件を適切に指定。
- 冪等性と部分失敗耐性:
  - DB 書き込みは冪等（DELETE → INSERT、ON CONFLICT を想定）で実装。部分失敗時に既存データを不必要に消さないよう、書き込むコードを絞る等の保護を行う。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants）呼出し失敗時は致命的に停止させず、ログ出力のうえ安全側のデフォルト（ゼロスコア等）で継続する方針。

### 修正 (Fixed)
- （初回リリースのため該当なし。実装は多くの例外処理・ログ出力・リトライ・バリデーションを含むため、運用でのフィードバックにより追って修正予定）

### 既知の制約・注意事項
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を利用する必要がある。未設定時は ValueError を送出する。
- .env の自動読み込みはプロジェクトルートが特定できない場合スキップされる。
- DuckDB の executemany に対する互換性（空リスト不可など）を考慮した実装を行っているため、古い DuckDB バージョンで検証が必要な場合がある。
- いくつかの DB 操作（market_calendar の保存等）は jquants_client に依存しているため、jquants_client の実装・例外ハンドリングの影響を受ける。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装（売買戦略→発注→監視の統合）。
- 単体テストの追加・モックを用いた外部 API テストの充実。
- 性能改善（大規模銘柄数時のバッチング・クエリ最適化）。

--- 

（注）この CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時には変更の粒度や担当者の意図に基づいて調整してください。