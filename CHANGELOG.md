Keep a Changelogに準拠した CHANGELOG.md（日本語）を以下に作成しました。

CHANGELOG.md
=============
すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に従います。
なお、本リリースはコードベースから推測した初期公開相当の内容を記載しています。

## [0.1.0] - 2026-03-31
初回リリース。主要な機能群（設定管理、データETL/カレンダー管理、リサーチ用ファクター計算、AIニュース解析・市場レジーム判定）を実装。

Added
-----
- パッケージ初期化
  - kabusys パッケージのバージョン情報を __version__ = "0.1.0" として公開。
  - パッケージの公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定をロードする Settings クラスを提供。
  - 自動 .env ロード機能（優先順位: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー実装
    - export KEY=val 形式対応、シングル/ダブルクォート文字列のエスケープ処理、インラインコメントの扱いをサポート。
  - 必須設定取得用の _require 関数（未設定時は ValueError を送出）。
  - 主要設定プロパティを提供（J-Quants、kabu API、Slack、データベースパス、監視閾値、環境モード検証、ログレベル検証など）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事のセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores テーブルへ書き込む score_news 関数を実装。
    - タイムウィンドウ計算（JSTベースの前日15:00〜当日08:30相当）を提供（calc_news_window）。
    - 銘柄ごとに記事を集約、最大記事数・文字数でトリムしてバッチ（最大20銘柄）で送信。
    - JSON Mode の応答パースとバリデーション、スコアの ±1.0 クリップ。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - API失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - テスト用に _call_openai_api をパッチ可能（unittest.mock.patch 推奨）。
  - regime_detector: ETF 1321 の 200日移動平均乖離とマクロニュースセンチメントを合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio 計算、マクロキーワード抽出、OpenAI 呼び出し（独立実装）による macro_sentiment 評価。
    - ルックアヘッドバイアス防止設計（target_date 未満のデータのみ参照、datetime.today() を直接参照しない）。
    - API失敗時は macro_sentiment=0.0 で継続。冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - リトライとエラーハンドリング（RateLimitError, APIConnectionError, APITimeoutError, APIError の取り扱い）。

- Research（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR、相対ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を参照して PER, ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB を利用した SQL ベースの実装、データ不足時の None 処理、結果は date/code キーの dict リストで返却。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコード < 3 の場合は None。
    - rank: 平均順位で ties を処理するランク付けユーティリティ（round で数値丸めを行い ties 検出安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
    - 標準ライブラリのみでの実装（pandas 等に依存しない）。

- Data（kabusys.data）
  - calendar_management
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar テーブルが未存在/未取得の場合は曜日ベース（土日非営業）でフォールバックする一貫性ある挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - pipeline / etl
    - ETLResult データクラス（取得/保存件数、品質検査結果、エラー一覧など）を公開。
    - ETL パイプライン設計の骨子（差分更新、保存、品質チェック）を実装方針として反映。

- モジュール再エクスポート
  - data.pipeline.ETLResult を kabusys.data.etl を通じて再エクスポート。

Changed
-------
- 初回リリースのため該当なし（初実装）。

Fixed
-----
- 初回リリースのため該当なし（既知の挙動は実装設計に反映済み）。

Security
--------
- OpenAI API キーは関数引数経由または環境変数 OPENAI_API_KEY で解決。キー未設定時は明示的に ValueError を送出して誤操作を防止。

Deprecated
----------
- 初回リリースのため該当なし。

Removed
-------
- 初回リリースのため該当なし。

Notes / 実装上の重要ポイント
-------------------------
- ルックアヘッドバイアス対策: AI / リサーチ系の関数は datetime.today() / date.today() を内部参照せず、呼び出し側が target_date を渡す設計。
- DB 書き込みは可能な限り冪等（DELETE→INSERT または ON CONFLICT 実装方針）で実装。部分失敗時に既存データを保護するため、書き込み対象を限定して置換する戦略を採用。
- OpenAI 呼び出しについてはリトライ・バックオフ・レスポンスバリデーションを導入し、API異常時は例外で停止させずフェイルセーフ（0.0 やスキップ）で継続する箇所がある。
- テスト容易性: OpenAI 呼び出しを行う内部関数（_call_openai_api）をパッチ可能にしてユニットテストで差し替えられるようにしている。
- DuckDB のバージョン依存（executemany の空リスト扱い等）を考慮した防御的実装が含まれる。

今後の想定追加（推測）
----------------------
- strategy / execution / monitoring モジュールの具体実装（現状はパッケージ公開のみ）。
- より詳細な品質チェック実装（kabusys.data.quality の拡張）。
- docs/Usage やサンプル ETL 実行スクリプト、CI 用のテストケース追加。

ライセンスや貢献に関する情報はリポジトリのルート（README.md 等）を参照してください。