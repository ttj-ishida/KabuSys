# CHANGELOG

すべての注目すべき変更点を記録します。セマンティックバージョニングに従っており、変更はカテゴリ別に整理しています（Added, Changed, Fixed, Deprecated, Removed, Security）。  

このファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-03-29

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）を追加。主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。

- 設定／環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を安全に読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml で探索（CWD に依存しない）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースは export 宣言、クォート文字列、インラインコメント等を考慮して堅牢に実装。
    - OS 側の既存環境変数を保護する protected ロジックを導入（override オプションあり）。
  - Settings クラスを提供し、アプリケーションで参照する主要設定プロパティをラップ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb） / SQLITE_PATH（data/monitoring.db）
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（許容値の検査）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント処理と市場レジーム判定を提供。
  - news_nlp.score_news:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ送信（最大 20 銘柄 / チャンク）、記事トリム（最大記事数・文字数制限）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数的バックオフでのリトライやフェイルセーフ（失敗時はスキップして継続）。
    - レスポンス検証ロジックを実装（JSON 抽出、results リスト、code/score のバリデーション、スコアのクリップ）。
    - DuckDB の executemany に関する互換性問題（空パラメータリスト不可）を考慮して部分的な DELETE → INSERT を実施。
    - test 用に内部 _call_openai_api を patch 可能（unittest.mock.patch による差し替え想定）。
  - regime_detector.score_regime:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM によるセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等的に書き込み。
    - マクロキーワードフィルタ、OpenAI 呼び出し（gpt-4o-mini）、API エラーに対するリトライ戦略、失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - 外部モジュール結合を避けるため、OpenAI 呼び出しは news_nlp と独立した実装。
    - 200 日分データ不足時のデフォルト中立処理などフェイルセーフを搭載。
  - 共通設計方針として、datetime.today() / date.today() を直接参照せず、target_date ベースで処理することでルックアヘッドバイアスを排除。

- データモジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー（market_calendar）管理ユーティリティを実装。
    - 営業日判定関数群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB の market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存するジョブ実装（バックフィル、健全性チェックあり）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - ETL パイプライン設計に基づくユーティリティ実装（差分取得、idempotent 保存、品質チェック連携の設計方針をコードドキュメントで明示）。
    - DuckDB のテーブル最大日付取得等のヘルパー実装。
  - jquants_client との連携を想定した設計（fetch / save を呼び出す箇所が存在）。

- Research モジュール（kabusys.research）
  - factor_research:
    - モメンタム、ボラティリティ、バリュー等の定量ファクター計算を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA に対する乖離）
      - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、平均売買代金、出来高比率
      - calc_value: PER（EPS が 0/欠損なら None）、ROE（raw_financials から最新値）など
    - 関数は DuckDB の prices_daily / raw_financials のみを参照し、本番注文系に影響しない設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、ランク相関（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - calc_ic はスピアマン ρ を計算し、データ不足時は None を返す。
    - rank は同順位の平均ランクを採用し丸め処理で ties 判定を安定化。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 環境変数の自動ロードにおいて OS 側既存の環境変数を保護する仕組み（protected set）を実装。自動読み込みを明示的に無効化できるフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

---

## 注意事項 / マイグレーションノート
- 環境変数
  - OpenAI API を利用する機能（news_nlp / regime_detector）は OPENAI_API_KEY の設定が必須（関数引数での注入も可能）。未設定時は ValueError が発生します。
  - 初期構成では JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の設定が必須となるプロパティがあります。設定が不足していると Settings が ValueError を投げます。
- DuckDB 互換性
  - DuckDB に対し executemany に空リストを渡すとエラーになる問題を回避するため、DELETE / INSERT の実行前にパラメータリストが空でないことを確認しています（news_nlp, pipeline 等）。
- テスト
  - OpenAI 呼び出し箇所はモジュール内の _call_openai_api を unittest.mock.patch で差し替え可能にしてあり、ネットワーク呼び出しをモックして単体テストが可能です。
- ルックアヘッド防止設計
  - LLM/ファクター計算/ETL 等の日時ロジックは target_date ベースで設計され、実行時の現在時刻参照によるルックアヘッドバイアスを排除しています。

---

このバージョンはプロジェクトの初期コア機能（データ ETL、カレンダー管理、因子計算、ニュース NLP、レジーム判定、設定管理）を一通り揃えたリリースです。今後はストラテジ、実行（execution）、モニタリング（monitoring）周りの機能拡充、テストカバレッジ強化、ドキュメント整備を予定しています。