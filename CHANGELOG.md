CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
リリースは安定版（セマンティックバージョニング）で管理します。

Unreleased
----------
（なし）

0.1.0 - 2026-04-02
------------------
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。
主にデータ取得/ETL、マーケットカレンダー、特徴量計算、AIによるニュース評価、
市場レジーム判定、設定管理のユーティリティ群を含みます。

Added
- パッケージ基礎
  - kabusys パッケージ初期実装（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, research, ai, monitoring（__all__ に登録）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルの自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - ロード優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーは export KEY=val 形式、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント処理に対応。
  - OS側の既存環境変数は保護（protected set）して上書き回避。
  - Settings クラス: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、データベースパス（DUCKDB_PATH、SQLITE_PATH）、監視関連閾値（CPU/MEM/DISK）、PID ファイルパス、実行環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）などをプロパティとして提供。入力検証（有効な env 値やログレベル検査）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を使用し、指定ウィンドウ（前日15:00 JST ～ 当日08:30 JST）内のニュースを銘柄別に集約。
    - OpenAI（gpt-4o-mini）を用いたバッチ評価。1回あたり最大20銘柄のチャンク処理、1銘柄あたり最大10記事・3000文字でトリム。
    - JSON Mode を期待し、レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - 成果物を ai_scores テーブルへ冪等的に書き換え（該当コードのみ DELETE → INSERT）し、部分失敗時に既存データを保護。
    - テスト容易性: OpenAI 呼び出し部分を patch して差し替え可能（内部の _call_openai_api）。
    - calc_news_window ユーティリティを提供（UTC naive datetime を返す）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照、OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価を行い、market_regime テーブルへ冪等書き込み。
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ挙動。
    - ルックアヘッドバイアスを防ぐ設計（date 比較は target_date 未満排他など）。
    - OpenAI 呼び出しの再試行・エラーハンドリング（RateLimit, APIConnectionError, APITimeoutError, APIError の区別）を実装。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（data.calendar_management）
    - market_calendar テーブルに基づく営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し、未登録日は曜日（週末）ベースでフォールバックする一貫したロジック。
    - カレンダー夜間バッチ更新 job (calendar_update_job): J-Quants API から差分取得・バックフィル（直近日数の再取得）・保存処理を実装。健全性チェック（未来日付の異常検知）あり。
    - 最大探索日数やバックフィル日数等の安全パラメータを設定（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。

  - ETL パイプライン（data.pipeline / data.etl）
    - ETLResult データクラスを公開（target_date、取得/保存件数、品質問題リスト、エラーリストなど）。to_dict により監査ログ向け辞書化を提供。
    - 差分取得、backfill、jquants_client を介した idempotent 保存（save_*）を想定。
    - 品質チェック（quality モジュール）との連携を前提。品質問題は収集して ETLResult に含める設計（Fail-Fast ではなく全件収集）。
    - ETL の設計上の注意: DuckDB の executemany に対する空リスト回避など互換性ケア。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: 約1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - Value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損時は None）。PBR/配当利回りは未実装として明記。
    - DuckDB SQL を用いた実装で、外部 API 呼び出し無し・本番発注 API へのアクセス無し。

  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装。
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を単一クエリで取得。
    - Spearman ランク相関（IC）計算。3件未満で None を返す等の堅牢性。
    - factor_summary により count/mean/std/min/max/median を計算。
    - rank ユーティリティは同順位を平均ランクで処理し、丸めによる tie 検出誤差対策あり。

- その他
  - 監視関連設定（config）に CPU/MEM/DISK のしきい値、PID ファイルパスを追加。
  - 多くの箇所で「ルックアヘッドバイアス防止」の設計を採用（datetime.today()/date.today() を内部で参照しない箇所の明記）。
  - テスト容易性のため一部の内部 API 呼び出しはモック差替え可能（例: _call_openai_api）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Known issues / Limitations
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する。
- news_nlp / regime_detector ともに gpt-4o-mini を想定したプロンプトおよび JSON Mode を使用。モデルの挙動や API 仕様変更により解析ロジックの調整が必要になる場合がある。
- PBR・配当利回りなど一部バリューファクターは未実装。
- DuckDB バインドや executemany の挙動に起因する互換性問題に注意（空リストは回避する実装）。
- raw_news.datetime は UTC 前提で処理（JST ⇔ UTC の扱いに注意）。

Acknowledgments / Notes
- コード内の docstring やコメントに設計方針（フェイルセーフ、ルックアヘッド回避、テスト容易性等）を明記しています。将来的な拡張（追加ファクター、発注モジュール、監視アラート等）を想定したモジュール分割になっています。