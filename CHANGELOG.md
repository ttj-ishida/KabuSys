# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム "KabuSys" のコアライブラリを公開します。主な追加機能・モジュールは以下の通りです。

### 追加
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__init__ の __version__ = "0.1.0"）。
  - 主要サブパッケージを __all__ でエクスポート（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定ロード機能を追加。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により CWD に依存しない .env ロードを実現。
  - .env / .env.local の読み込み優先順（OS 環境変数 > .env.local > .env）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを実装。
  - .env パーサー実装（コメント、export 句、クォートとエスケープ処理をサポート）。
  - Settings クラスを提供し、主要設定をプロパティで取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL 検証
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数未設定時に明確な ValueError を送出。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダー管理と夜間バッチ更新ジョブ（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - market_calendar 未取得時は曜日ベースのフォールバック、DB 値優先の一貫した動作。
    - 最大探索日数やバックフィル、健全性チェックを実装。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）設計に基づく ETL パイプライン補助。
    - DuckDB を用いた最大日付取得やテーブル存在チェック等のユーティリティを提供。
  - jquants_client と連携する保存処理想定（fetch/save の呼び出しを行う設計箇所を用意）。

- AI（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols からニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を算出・ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
    - バッチ処理（1 API コールで最大 20 銘柄）、1銘柄あたり記事数・文字数上限（トリム）によるトークン肥大化対策を実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）をエクスポネンシャルバックオフで行い、API 失敗時はフェイルセーフでスキップ（例外を投げず継続）。
    - レスポンス検証ロジックを実装（JSON 復元、results 配列検証、コード照合、数値検証、スコアの ±1.0 クリップ）。
    - DB 書き込みは部分失敗に強い設計（成功した銘柄のみ DELETE→INSERT で置換）。
    - score_news(conn, target_date, api_key=None) を公開。OpenAI API キーが未設定の場合は ValueError。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（マクロキーワードリスト） → OpenAI 呼び出し（gpt-4o-mini）→ スコア合成 → DB 書き込みを実装。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - score_regime(conn, target_date, api_key=None) を公開。OpenAI API キーが未設定の場合は ValueError。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等の計算を DuckDB SQL で実装。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が無効な場合は None）。
    - 設計として、外部 API へアクセスせず DB のみ参照する安全な実装。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: スピアマン順位相関（Information Coefficient）を実装（結合、欠損除外、最小サンプルチェック）。
    - rank: 同順位は平均ランクで扱うランク関数（丸め対策あり）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。

### 変更
- （初版のため変更履歴はありません）

### 修正
- （初版のため修正履歴はありません）

### 注意事項 / 実装ノート
- OpenAI 呼び出し
  - news_nlp と regime_detector はいずれも gpt-4o-mini を想定し JSON Mode を利用する設計。API キーは引数で注入可能（テスト性向上）で、引数未指定時は環境変数 OPENAI_API_KEY を参照します。
  - API 失敗に対するフェイルセーフ（スコア 0.0 で継続や該当チャンクをスキップ）を採用しており、致命的な停止を避ける設計です。
- データベース
  - DuckDB を前提とした SQL 実装。executemany に空リストを渡せない DuckDB の互換性制約を考慮した実装（空チェックあり）。
- ルックアヘッドバイアス対策
  - 日付処理で datetime.today() / date.today() を内部で参照しない方針（引数として与える target_date ベースで判定）。これによりバックテスト等でのルックアヘッドバイアスを防止。
- .env パーサー
  - export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなど多くの実用ケースに対応。
- ログと検証
  - 設定値（KABUSYS_ENV / LOG_LEVEL）や各種処理で不正値検出時に ValueError を返し早期に問題を発見できるようにしています。

今後の予定（想定）
- Strategy / execution / monitoring サブパッケージの実装拡充（注文実行ロジック、監視・アラート機構など）。
- テストカバレッジ拡充、外部 API クライアント（J-Quants / kabuapi）周りのモック化と統合テストの追加。
- パフォーマンス最適化および数値検証（ファクターの回帰検証など）。

---
この CHANGELOG はコードベースからの推測に基づき作成しています。実際のリリースノートにする際は必要に応じて加筆・修正してください。