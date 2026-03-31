# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__init__、バージョン 0.1.0）。
  - モジュール公開インターフェース定義（__all__）を整備。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行うため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - OS 環境変数を保護する protected 機構（上書き防止）を実装。
  - .env パーサーを実装（コメント、export プレフィックス、クォート・エスケープ対応、インラインコメント処理等）。
  - Settings クラスを追加し、主要な設定値をプロパティ経由で取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/... のバリデーション）
    - ヘルパー bool プロパティ: is_live / is_paper / is_dev

- AI（OpenAI）統合機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを評価し、ai_scores テーブルに書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）および calc_news_window ユーティリティを提供。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、記事数および文字数トリム、JSON Mode レスポンスの検証・パース、スコアの ±1.0 クリップを実装。
    - リトライ/バックオフ処理（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。API 呼び出しはテスト時に差し替え可能（_call_openai_api を patch 可能）。
    - DuckDB への冪等的な書き込み（DELETE → INSERT、executemany 前の空チェック対応）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みを行う score_regime を実装。
    - マクロニュース抽出、OpenAI 呼び出し、マクロスコアのリトライ/フォールバック（失敗時 macro_sentiment=0.0）、スコア合成と閾値判定を実装。
    - LLM 呼び出しは news_nlp と独立して実装し、モジュール結合を低減。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラス（取得/保存数、品質問題、エラー等を保持）を実装。
    - 差分取得、バックフィル日数、品質チェックの概念と DB 最終日取得ユーティリティを実装。
  - ETL の公開インターフェース（kabusys.data.etl）として ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を基にした営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日）を採用。
    - calendar_update_job を実装し、J-Quants から差分取得して冪等保存（バックフィル、健全性チェック含む）を行う。J-Quants クライアント呼び出しは外部モジュール（jquants_client）経由。
  - DuckDB 操作用のユーティリティ（テーブル存在チェック・日付取得等）を実装。

- リサーチ（kabusys.research）
  - ファクター計算群（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ/流動性（20 日 ATR、平均売買代金、出来高比率）、バリュー（PER、ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB SQL を用いた高速な一括取得処理を採用。データ不足時の None ハンドリングを実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンを一度に取得する SQL 実装。
    - IC（Information Coefficient）計算（calc_ic）: ランク相関（Spearman）を実装。必要レコード数チェック（最小 3 件）。
    - ランク化ユーティリティ（rank）: 同順位は平均ランクで処理、数値丸めで ties を安定化。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照する実装とし、コード内にハードコーディングしない設計。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、全モジュールで datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る API を採用。
- 外部 API 呼び出しはフェイルセーフ設計（API 失敗時は logging に WARN を残し、可能な範囲で継続）とし、重要な DB 書き込み失敗は上位へ例外伝播。
- テスト容易性を考慮し、外部 API 呼び出し箇所（OpenAI 呼び出し等）は関数レベルで差し替え可能に実装。

---

今後の予定（例）
- ETL 実行スケジューラ / CLI の追加
- モデル評価用のテストデータセットと CI の整備
- 発注・実行部分（execution モジュール）と監視（monitoring）モジュールの拡充

--- 

（注）この CHANGELOG は現行のコードベースから推測して作成したリリースノートです。実際のリリース方針や日付はプロジェクト方針に応じて調整してください。