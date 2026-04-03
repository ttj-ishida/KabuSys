CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。
フォーマット: https://keepachangelog.com/ja/

0.1.0 - 2026-04-03
------------------

Added
- 全体
  - 初回リリース。パッケージ名: kabusys（日本株自動売買システムの基盤ライブラリ）。
  - パッケージバージョンを __version__ = "0.1.0" として公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出機能を追加（.git または pyproject.toml を基準に探索）。
  - .env パーサーを実装し、コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動読み込みの優先順位を実装: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 既存 OS 環境変数を保護する protected 機構（.env 上書き制御）を実装。
  - Settings クラスを公開（settings インスタンス）。J-Quants / kabuステーション / LINE / DB /監視 /システム設定のプロパティを提供。
  - 環境値のバリデーション (KABUSYS_ENV, LOG_LEVEL) と関連ユーティリティプロパティ (is_live/is_paper/is_dev) を追加。
  - 必須環境変数未設定時に ValueError を投げる _require 実装。

- データ / ETL (kabusys.data)
  - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
  - pipeline モジュール実装（ETLResult を含む）。ETL 実行結果、品質チェック、エラー集約などを管理する構造を提供。
  - calendar_management モジュールを追加（JPX カレンダー管理、営業日判定、next/prev/get_trading_days、SQ 判定、夜間バッチ更新 job 実装）。
    - market_calendar が未取得の場合に曜日ベースのフォールバックを行う設計。
    - カレンダー差分取得・バックフィル・健全性チェック・IDEMPOTENT 保存（ON CONFLICT 相当）フローを実装。
    - 最大探索範囲制限や未来日健全性チェック等の安全策を導入。
  - jquants_client を経由したカレンダー取得/保存の呼び出し点を用意。
  - DuckDB を前提としたテーブル存在チェック等のユーティリティを追加。

- AI / ニュースNLP (kabusys.ai)
  - news_nlp モジュールを実装:
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini）に JSON mode で問い合わせてセンチメントスコアを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を算出する calc_news_window を公開。
    - バッチ処理 (_BATCH_SIZE=20)、銘柄ごとの上限記事数・文字数トリム、リトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンスの厳密バリデーションとスコアの ±1.0 クリップ、部分失敗時の DB 保護（対象コードのみ DELETE→INSERT）を実装。
    - score_news(conn, target_date, api_key=None) を公開。書き込み件数（銘柄数）を返す。API キー未設定時は ValueError。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能に設計（内部 _call_openai_api をパッチ可）。
  - regime_detector モジュールを実装:
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）判定を実装。
    - prices_daily / raw_news からのデータ取得、ma200_ratio 計算、マクロキーワードによるニュース抽出、OpenAI（gpt-4o-mini）での JSON 出力を想定したセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出し失敗時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフを採用。
    - score_regime(conn, target_date, api_key=None) を公開。API キー未設定時は ValueError。

- Research（因子・特徴量） (kabusys.research)
  - factor_research モジュールを実装:
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高変化率）、バリュー（PER, ROE）を DuckDB SQL によって計算する関数を実装。
    - calc_momentum, calc_volatility, calc_value を公開。各関数は date / code ベースの dict リストを返す。
    - 欠損やデータ不足時の扱い（例: MA200 データ不足時は None を返す）を明確に設計。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 与えられた horizons（デフォルト [1,5,21]）に対する将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）の場合は None を返す。
    - rank: 同順位は平均ランクを返すランク関数（浮動小数点の丸め対策あり）。
    - factor_summary: 指定カラムごとの count/mean/std/min/max/median を計算。
  - 研究用ユーティリティとして kabusys.data.stats.zscore_normalize を re-export。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- OpenAI API キーは引数で注入可能。未設定時は明示的に ValueError を発生させる箇所あり（安全な失敗）。
- .env 自動ロードで OS 環境変数が上書きされないよう保護機構を実装。

Notes / 設計上の重要なポイント
- ルックアヘッドバイアス防止: 各 AI / リサーチ関数は内部で datetime.today() / date.today() を参照せず、target_date 指定に完全に依存する設計。
- DB 書き込みは冪等性を重視（多くの箇所で DELETE→INSERT のパターン、BEGIN/COMMIT/ROLLBACK を使用）。
- OpenAI 呼び出しは JSON mode 想定だが、実運用ではレスポンスの前後テキスト混入に対する回復処理を実装。
- API 呼び出しの失敗はフェイルセーフで継続する設計（スコアを 0 にフォールバック、または該当チャンクをスキップ）。
- DuckDB executemany における空リスト取り扱いや互換性制約への対処を行っている。

Known limitations
- PBR、配当利回りなどのバリューファクターは未実装（calc_value で言及）。
- news_nlp / regime_detector ともに gpt-4o-mini に依存する設計（モデル変更はパラメータ修正が必要）。
- jquants_client 等の外部クライアント実装に依存する箇所がある（テスト時はモック化が必要）。

今後の予定（例）
- 追加指標（PBR、配当利回り等）の実装。
- モデル切替のための抽象化・設定拡充。
- テストカバレッジの拡充（特に外部 API のフェイルパス、.env パーサーのエッジケース）。

-----------

（注）本 CHANGELOG は与えられたコード内容からの推定に基づいて作成しています。実際のリリースノートはプロジェクト方針・コミット履歴に合わせて調整してください。