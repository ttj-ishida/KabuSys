# Changelog

すべての変更は Keep a Changelog の原則に従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。  

## [0.1.0] - 2026-03-29

初回リリース — 日本株自動売買システム「KabuSys」の公開バージョン。主要機能と実装の概要を以下に示します。

### 追加（Added）
- パッケージ初期構成
  - パッケージトップ: kabusys.__init__ にてバージョン定義と主要サブパッケージの公開 (data, strategy, execution, monitoring) を追加。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env / .env.local を自動でプロジェクトルート（.git または pyproject.toml 基準）から読み込む自動ロード機能を実装。
  - .env パーサーの実装: export プレフィックス、クォート処理、インラインコメントの扱い、保護された OS 環境変数（override/ protected）などに対応。
  - 自動ロード無効化のためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加し、J-Quants や kabuステーション、Slack、DBパス、実行環境（development/paper_trading/live）、ログレベル等の取得を提供。
  - デフォルト値: KABUSYS_API_BASE_URL、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）等。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント分析（news_nlp.py）
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別スコア（-1.0〜1.0）を取得して ai_scores テーブルへ保存。
    - バッチ処理（最大20銘柄／チャンク）、記事数・文字数トリム、レスポンス検証、スコアクリップ処理を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。失敗はフェイルセーフでスキップし、処理継続。
    - テスト用に内部の API 呼び出し関数を差し替え可能（unittest.mock.patch で _call_openai_api を差替え可）。
    - calc_news_window: JST基準のニュース収集ウィンドウ計算（前日15:00～当日08:30 JST 相当の UTC naive 範囲）。

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースの LLMセンチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を決定して market_regime テーブルへ冪等書き込み。
    - prices_daily 及び raw_news を参照、OpenAI 呼び出しは独立実装、API失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - リトライ・バックオフ、JSON パースの堅牢化、ログ出力を実装。

- データ基盤（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルの有無に依存しない一貫した営業日判定関数群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は曜日ベース（土日を非営業日）でフォールバック。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。

  - ETL パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分更新ロジック、backfill の既定値、品質チェック（quality モジュールを参照）との連携設計。
    - DuckDB を前提とした最大日付取得、テーブル存在チェック等のユーティリティを実装。

- 研究・ファクター群（src/kabusys/research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR / 相対ATR / 平均売買代金 / 出来高比率）、Value（PER・ROE）の計算を実装。prices_daily / raw_financials のみ参照。
    - DuckDB SQL を多用し、データ不足時は None を返す方針。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズンの LEAD を用いた fwd_Nd 計算）、IC（Spearman rank）計算、ランク変換、統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで完結。
  - research パッケージの __init__ で zscore_normalize 等のユーティリティを再公開。

### 変更（Changed）
- （初回リリースのため該当なし）  

### 修正（Fixed）
- （初回リリースのため該当なし）  

### 既知の制限 / 注意事項（Notes）
- OpenAI 関連機能は API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必要とします。未指定の場合は ValueError を送出します。
- news_nlp の出力検証は堅牢化しているが、LLM の想定外出力や未知のコードは無視する実装になっています（部分的にスコアが取得できない銘柄が出る可能性あり）。
- calc_value では PBR・配当利回りなどは未実装（ドキュメントに記載の通り）。
- DuckDB の executemany に空リストバインドできない点を考慮した実装になっており、バージョン互換性に配慮しています。
- 日時の扱いはすべて naive date/datetime（タイムゾーンを持たない）で統一しています。news ウィンドウは JST を基準に UTC naive に変換して DB と比較します。
- ルックアヘッドバイアスに対する対策として、関数内部で datetime.today()/date.today() を直接参照しない実装方針を採用しています（target_date を明示的に渡す設計）。

### セキュリティ（Security）
- 環境変数の自動ロードでは OS 環境変数が保護され、.env の上書きを防ぐ機構を導入しています。
- 外部 API（OpenAI/J-Quants/kabu API）のエラーをフェイルオーバー・ログ記録し、致命的なキー未設定は明示的な例外で通知します。

### 互換性（Compatibility / Breaking Changes）
- 初回リリースのため破壊的変更はありません。

---

貢献・バグ報告・改善提案は issue を立ててください。今後のリリースで改善点（API レスポンス検証の強化、追加ファクター、注文実行ロジックの統合など）を反映予定です。