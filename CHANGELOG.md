CHANGELOG
=========

すべての重要な変更点は Keep a Changelog のフォーマットに従って記載しています。  
日付はリリース作成日時（リポジトリから推測した最初のリリース: 2026-04-02）です。

Unreleased
----------
（現時点のコードベースは初期リリースの内容に基づくため未リリースの変更はありません）

[0.1.0] - 2026-04-02
-------------------

Added
- パッケージ初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env ファイルのパース機構を実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント取り扱い、無効行のスキップ等に対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB /監視設定 等のプロパティを環境変数から取得。必要な環境変数が未設定の場合は明確な ValueError を送出。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）と利便性プロパティ（is_live, is_paper, is_dev）を実装。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini、JSON Mode）にバッチ送信してセンチメントスコアを算出し、ai_scores テーブルへ冪等的に保存する機能を実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）や記事トリミング（記事数・文字数制限）を実装。
  - バッチサイズ、リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで処理する堅牢な実装。
  - API レスポンスのバリデーション機構（JSON 抽出・形式チェック・未知コード無視・数値検査）とスコアの ±1.0 クリッピング。
  - テスト容易性のため OpenAI 呼び出し関数を patch 可能にし、失敗時はフォールバックして継続する設計（フェイルセーフ）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
  - DuckDB からの MA 計算、マクロニュース抽出、OpenAI 呼び出し、スコア合成、閾値判定を含むパイプラインを実装。
  - API 呼び出しのリトライ/バックオフ、API エラーやパース失敗時は macro_sentiment=0.0 にフォールバックする安全策を採用。
  - ルックアヘッドバイアス回避のため内部実装で datetime.today()/date.today() を直接参照しないよう設計。

- データ ETL / パイプライン（kabusys.data.pipeline / kabusys.data.etl）
  - ETLResult データクラスを実装し、ETL 処理の実行結果（取得・保存レコード数、品質問題、エラー等）を一元管理できるようにした。
  - 差分更新・バックフィル・品質チェックを想定した設計方針とユーティリティ関数を追加（テーブル存在チェック、最大日付取得などの内部ユーティリティ）。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を追加。J-Quants クライアント経由で差分取得・冪等保存を行う。
  - 営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - DB データ優先で、未登録日は曜日ベースのフォールバックを行う一貫したロジック。
  - 探索上限日数（_MAX_SEARCH_DAYS）やバックフィル、健全性チェックなどを導入して安全性を確保。

- リサーチ（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）等のファクター計算関数を実装。DuckDB SQL を活用し prices_daily/raw_financials のみ参照する純粋計算ロジック。
  - feature_exploration: 将来リターン計算（複数ホライズン）、IC（スピアマン ρ）計算、ランク変換、統計サマリー（count/mean/std/min/max/median）を実装。外部ライブラリに依存しない実装。
  - research パッケージで主要なユーティリティを公開（zscore_normalize は data.stats から再エクスポート）。

- DuckDB を中心とした設計
  - 各モジュールは DuckDB 接続を受け取り、SQL + Python による処理でデータ取得・集計・書き込みを行う設計。実運用 DB への影響を考慮して冪等書き込み（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）を採用。

- ロギングと例外処理
  - 各処理で詳細な情報・警告・例外ログを出力するように実装。DB 書き込み失敗時のロールバックや警告の記録などを配慮。

Changed
- n/a（初回リリースのため過去からの変更はありません）

Fixed
- n/a（初回リリースのためバグ修正履歴はありません）

Security
- 環境変数の取扱いに注意
  - 必須 API キー（OPENAI_API_KEY 等）未設定時は明示的に ValueError を送出することで誤設定を早期検出。
  - .env 自動ロード時、既存の OS 環境変数を保護するため protected セットを導入し .env の上書きを制御。

Notes / 実装上の設計判断（要約）
- ルックアヘッドバイアス回避: AI スコア・レジーム判定・ニュース集計などの日次処理は内部で現在日を直接参照せず、呼び出し側が target_date を明示的に渡す設計。
- フェイルセーフ: 外部 API（OpenAI、J-Quants）失敗時は処理継続（部分スキップ/フォールバック）を優先し、運用での単一障害点を緩和。
- テスト容易性: OpenAI 呼び出しを patch できるように分離して実装（ユニットテストでの差替えを想定）。
- DuckDB のバージョン差（executemany の空リスト扱い等）に配慮した実装や互換性処理を含む。

公開 API（主要）
- kabusys.settings: 環境設定アクセス
- kabusys.ai.score_news(conn, target_date, api_key=None): ニューススコアリング（ai_scores へ書き込み）
- kabusys.ai.score_regime(conn, target_date, api_key=None): 市場レジーム判定（market_regime へ書き込み）
- kabusys.data.pipeline.ETLResult: ETL 実行結果のデータクラス
- kabusys.data.calendar_management: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
- kabusys.research: ファクター計算・探索関連関数群

要望や追加情報（もしあれば）
- CHANGELOG にさらに具体的な変更日・コントリビュータ・関連 Issue 番号等を追加したい場合は、その情報を提供してください。