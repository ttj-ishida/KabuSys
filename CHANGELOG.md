# Keep a Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- ルール: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （次リリースに向けた変更があればここに記載します）

## [0.1.0] - 2026-04-01
初回公開リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージを導入。バージョン 0.1.0 をパッケージメタ情報として設定。
  - パブリック API: data, strategy, execution, monitoring を __all__ として公開。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env（プロジェクトルートを .git または pyproject.toml で探索）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視 / システム関連の設定プロパティを公開。
  - 必須環境変数取得時に未設定なら ValueError を送出するユーティリティを提供。
  - KABUSYS_ENV および LOG_LEVEL の許容値検証を実装（不正値は ValueError）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメント解析（news_nlp.score_news）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別スコアを ai_scores テーブルへ書込む。
    - リクエストチャンクサイズ、トークン肥大対策（記事最大数・文字数トリム）を実装。
    - JSON Mode を想定したレスポンスの厳密バリデーション、無効レスポンスの保護、スコアの ±1.0 クリップ。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ付きリトライを実装。その他の例外はスキップして継続（フェイルセーフ）。
    - テスト用フック: _call_openai_api を patch 可能。
    - 時刻ウィンドウ計算ユーティリティ calc_news_window を提供（JST 前日 15:00 ～ 当日 08:30 に対応した UTC naive datetime を返す）。
    - DB 書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT で上書き（冪等性確保）。

  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を決定。
    - マクロニュース抽出用のキーワードリストと、OpenAI（gpt-4o-mini）呼び出し、JSON パース、リトライ・フェイルセーフロジックを実装。
    - DuckDB の prices_daily/raw_news/market_regime を用いて、ルックアヘッドバイアスを防ぐため target_date 未満データのみ参照。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等手順とロールバックハンドリングを実装。
    - API キー注入（api_key 引数）に対応。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。

- データ関連（kabusys.data）
  - ETL パイプラインのインターフェース（pipeline.ETLResult）を公開。
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを参照して営業日判定／next/prev/get_trading_days／SQ判定を提供。
    - DB 登録がないまたは未設定値のある日については曜日ベース（土日）でのフォールバックを行い、一貫性を保持。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants クライアントを用いて差分取得・冪等保存・バックフィルを実行。
    - 異常検知（極端に未来日が登録されている等）のガードを実装。

  - ETL パイプライン（pipeline）
    - ETLResult データクラスを実装。取得・保存件数、品質問題、エラー一覧等を保持。
    - テーブル存在確認や最大日付取得等のユーティリティを実装（DuckDB 前提）。
    - ETL の設計方針として差分更新、バックフィル、品質チェックの収集（Fail-Fast にはしない）を明示。

- Research モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6Mリターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）計算を実装。
    - DuckDB SQL を活用し、prices_daily / raw_financials のみ参照。「本番口座・発注 API にはアクセスしない」方針。
    - データ不足時は None を返す挙動を明示。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンに対する将来終値リターンを計算。horizons のバリデーションを実装。
    - IC（Information Coefficient）: スピアマン相関（ランク）によるファクター有効性評価 calc_ic を実装。十分な有効レコードがない場合は None を返す。
    - 基本統計量（factor_summary）と rank ユーティリティを提供。
  - data.stats の zscore_normalize を再エクスポート（__init__.py 経由）。

### 変更
- なし（初回リリース）

### 修正（バグ）
- なし（初回リリース）

### 既知の制約・注意事項
- DuckDB を前提とした SQL 実装のため、対象テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が事前に作成されている必要があります。
- OpenAI 呼び出しは gpt-4o-mini を想定しており、API キーは api_key 引数または環境変数 OPENAI_API_KEY で与える必要があります。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない設計です（テスト時は個別に patch してください）。
- research モジュールは外部 API に一切アクセスしない設計です（分析用途で安全）。
- 一部 DuckDB のバージョン差異（executemany に空リストを渡せない等）に配慮した実装が入っています。
- 日付/時刻の扱い: ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計が多く採用されています（一部バッチジョブのみ date.today() を使用）。

### 将来の改善候補（メモ）
- OpenAI のレスポンス検証・プロンプト改善による堅牢性向上。
- ai_scores / market_regime 等の書き込みパフォーマンス改善（バルク操作の最適化）。
- calendar_update_job の詳細な retry/バックオフ戦略実装。
- unit/integration テストの追加（特に外部 API 絡み）。

---

以上。必要であれば各モジュールごとの詳細なドキュメントやリリースノートのセクション分割（Breaking Changes / Migration）を追記します。どの程度の粒度で残すか指示ください。