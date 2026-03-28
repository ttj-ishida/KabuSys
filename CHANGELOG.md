Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。パッケージのバージョンは src/kabusys/__init__.py の __version__ を元に 0.1.0 とし、リリース日を現在日付（2026-03-28）で記載しています。必要があれば日付や文言を調整してください。

CHANGELOG.md
-------------

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-28

### Added
- 基盤パッケージ構成を追加
  - パッケージ名: kabusys（バージョン 0.1.0）
  - エクスポートモジュール: data, strategy, execution, monitoring（__all__ を通して公開）

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装
  - プロジェクトルートは __file__ を基準に .git または pyproject.toml から探索（CWD に依存しない）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサーは `export KEY=val`、クォート（シングル/ダブル）、エスケープ、行内コメント等に対応
  - .env 上書き時に OS 環境変数を保護する protected キーセットの概念を導入
  - Settings クラスを提供（J-Quants・kabu API・Slack・DB パス・環境種別・ログレベルなどのプロパティ）
  - 必須環境変数未設定時は ValueError を送出する _require を提供
  - KABUSYS_ENV と LOG_LEVEL の有効値チェックを実装

- AI 関連（kabusys.ai）
  - news_nlp モジュール
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメントを評価し ai_scores テーブルへ書き込む機能（score_news）
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST の記事）を正確に計算する calc_news_window を実装（UTC 変換済）
    - 銘柄ごとに記事を集約し、1 銘柄あたり記事数上限／文字数上限でトリム
    - 最大バッチサイズ（_BATCH_SIZE）で複数銘柄をまとめて API コール
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数的バックオフ + リトライ
    - API レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score チェック、数値・有限性チェック）
    - スコアは ±1.0 にクリップ、部分成功時は該当コードのみ置換（DELETE → INSERT）して既存データ保護
    - テスト容易性のため _call_openai_api を差し替え可能に設計
    - API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError

  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み合成して市場レジーム（bull/neutral/bear）を判定する score_regime を実装
    - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）
    - マクロニュースは raw_news からキーワードでフィルタして最大件数まで取得
    - OpenAI（gpt-4o-mini）でマクロセンチメントを JSON で取得。429 等に対するリトライおよび 5xx の扱いを明確化
    - 計算結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API キー注入可能（api_key 引数）でテスト容易性・安全性を確保

- 研究（research）モジュール
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（prices_daily を参照）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（EPS が不適切な場合は None）
    - データ不足時や条件に合わないケースは None を返すなど堅牢に実装
  - feature_exploration
    - calc_forward_returns: 与えた horizons（デフォルト [1,5,21]）に対する将来リターンを一括 SQL で取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（結合・None 排除・最小データ数チェック）
    - rank: 同順位の平均ランク計算を含むランク関数（小数丸めで ties を扱う）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出
  - いずれも外部ライブラリ（pandas 等）に依存しない実装、DuckDB を利用

- データプラットフォーム（data）
  - calendar_management
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定・探索 API を提供
    - market_calendar が未取得の場合は曜日ベース（土日休）でフォールバック
    - DB 登録値優先、未登録日は曜日フォールバックで一貫性を維持
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等保存。バックフィル・先読み日数・健全性チェックを実装
  - pipeline / etl
    - ETLResult dataclass を実装（取得/保存件数、quality_issues、errors、ユーティリティメソッド to_dict 等）
    - ETL パイプライン設計に基づく差分取得 / 保存 / 品質チェックのためのユーティリティを実装（jquants_client / quality と連携）
    - data.etl は ETLResult を再エクスポート（公開インターフェース）

- 汎用設計方針の採用
  - ルックアヘッドバイアスを避けるためモジュール内で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計を徹底
  - DuckDB を主要なデータストアとして使用し、SQL と Python を組み合わせて処理
  - API 呼び出しの失敗はフェイルセーフとして継続可能（スコア 0.0 / スキップ等）に設計
  - 単体テスト容易性のため外部呼び出し（OpenAI クライアント等）は注入・パッチ可能に実装

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes（利用上の注意）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OPENAI_API_KEY は AI モジュールを実行する場合に必要（api_key 引数でも指定可能）
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- ログレベル・環境: KABUSYS_ENV は development / paper_trading / live のいずれか、LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL
- テスト時の便利機能:
  - _call_openai_api を patch して OpenAI 呼び出しをモック可能
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で .env の自動ロードを抑止

---

上記はコードから推測してまとめた CHANGELOG です。ドキュメントやリリースノートとして追加・修正したい点（公開日を別にする、個別の不具合修正を明記する、既知の制限を追加する等）があれば指示ください。