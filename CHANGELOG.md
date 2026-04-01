Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。
リリース日付はパッケージのスナップショットから推測して記載しています。

[Unreleased]
------------

なし

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース "kabusys"（__version__ = "0.1.0"）。
  - パッケージエントリポイント: src/kabusys/__init__.py（data, strategy, execution, monitoring を公開）。
- 環境設定管理（src/kabusys/config.py）
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）による .env 自動読み込み。
  - .env/.env.local の読み込み順序と上書きルールを実装（OS環境変数を protected として保持、.env.local で上書き可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - 複雑な .env 行パース対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベース / 監視 / システム設定等の環境変数をプロパティ経由で取得。必須値未設定時は ValueError を送出。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）。
  - デフォルト設定（duckdb/sqlite パス、PID ファイルパス、閾値等）を持つ。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - JST タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と UTC 変換用ユーティリティ（calc_news_window）。
    - バッチサイズ、記事・文字数のトリム制御（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）。
    - JSON Mode レスポンスの堅牢なパースとバリデーション（results 配列・code/score 検証・数値クリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT）時の部分失敗保護（影響対象コードのみ置換）。
    - テスト容易性のため OpenAI 呼び出しを差し替えられる設計（_call_openai_api をモジュール内でパッチ可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio: 最新終値 / MA200）とマクロセンチメント（LLM）を重み付け合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタして LLM に渡す処理（最大記事数制限）。
    - OpenAI 呼び出しのリトライ・フォールバック（API エラー時は macro_sentiment = 0.0）。
    - レジーム判定結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - LLM 呼び出しは news_nlp と分離して実装（モジュール結合を避ける）。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基にした営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データが無い／未登録日の場合は曜日ベース（土日休み）でフォールバック。
    - JPX カレンダーを J-Quants から差分取得して保存する夜間ジョブ（calendar_update_job）を実装。バックフィル・健全性チェックを備える。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass による ETL 実行結果の集約（取得件数、保存件数、品質問題、エラーの集計）。
    - 差分更新・backfill・品質チェック（quality モジュール連携）を想定した ETL 設計。
    - jquants_client を通じた idempotent 保存（save_*）を前提。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- 研究用ユーティリティ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 内 SQL を用いて計算。
    - データ不足時は None を返す一貫した挙動。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: Spearman のランク相関）、ランク変換（rank）、ファクター統計サマリー（factor_summary）。
    - pandas 等の外部依存を持たず標準ライブラリ + DuckDB SQL で実装。
  - research パッケージ __all__ に主要関数を公開。

- 共通ユーティリティ
  - DuckDB 互換性に配慮した実装（executemany の空リスト制約を考慮したガード等）。
  - ロギングを適切に追加（各主要関数で info/debug/warning を出力）。

Security
- OpenAI API キー / 各種トークンは環境変数で取得（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。未設定時は明示的なエラー（ValueError）を出す箇所があるため、運用時は .env 等での管理が必要。
- .env 読み込みはデフォルトで有効。OS 環境変数は保護（.env による上書きを制限）される挙動。

Notes / Known constraints
- OpenAI 呼び出しは gpt-4o-mini（JSON Mode）を前提としている。レスポンスの形式変更やモデル変更はパーサ側の調整が必要。
- LLM 呼び出しはフェイルセーフ設計（API エラーや解析失敗時はスコアを 0.0 にフォールバック、または該当コードをスキップ）となっており、例外を投げずに処理を継続する箇所がある。
- DuckDB のバインド挙動に関する互換性注意（executemany に空リストを渡せない点など）を考慮した実装になっている。
- 日付処理はルックアヘッドバイアス回避のため、date.today() / datetime.today() をスコープ内で直接参照しない設計（target_date 引数駆動）。
- テスト容易性のため、OpenAI への実ネットワーク呼び出しを差し替えられるフック（モジュール内の _call_openai_api のパッチ）が用意されている。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 秘匿情報は環境変数経由で取得する設計。自動的にファイルへ書き出す機能は含まれない。

開発者向けメモ
- テスト時に .env 自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は unit test で差し替え可能です（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- ETL / calendar 更新は jquants_client に依存するため、実行時には J-Quants の認証情報（JQUANTS_REFRESH_TOKEN 等）を用意してください。

-----------------------------------------------------------------------------