# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース方針: 意味のある新機能追加や設計上の重要点・既知の挙動を中心に記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-01
初期リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの公開モジュール: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
  - パッケージバージョン: 0.1.0。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォートの有無で挙動を区別）
  - Settings クラスを提供（プロパティ経由で J-Quants / kabu / Slack / DB パス / 監視閾値 / 環境判定等の設定を取得）。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証（不正値で ValueError を送出）。

- AI: ニュース NLP と市場レジーム判定 (src/kabusys/ai/)
  - news_nlp.score_news:
    - raw_news と news_symbols を使い、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）にバッチ送信しセンチメント（-1.0〜1.0）を算出。
    - チャンク処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数・文字数上限でトリム。
    - JSON Mode のレスポンス検証・復元（前後余計なテキストが混ざる場合の {} 抽出）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保護するため、書き込みは対象コードに限定して DELETE → INSERT。
    - DuckDB 0.10 の executemany の挙動（空リスト不可）に配慮した実装。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成し、市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロセンチメントは OpenAI（gpt-4o-mini）呼び出しに対して JSON 出力を要求し、API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - DuckDB の prices_daily / raw_news を参照。ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用。
    - 内部で OpenAI クライアント呼び出しはテスト用に差し替え可能（ユニットテスト向け）。

- Research（ファクター計算 / 特徴量探索） (src/kabusys/research/)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。必要行数未満は None。
    - calc_value: raw_financials から直近の財務データを取得し PER / ROE を計算。EPS が 0/欠損なら per は None。
    - 設計上、prices_daily / raw_financials のみ参照し、外部 API へのアクセスはなし。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンの検証（1〜252）有り。
    - calc_ic: ファクター値と将来リターン間の Spearman ランク相関（IC）を計算。データ不足時は None。
    - rank: 同順位は平均ランクを与えるランキング実装（丸めによる ties 対応）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を返す。
  - 研究系は標準ライブラリ中心の実装で pandas 等に依存しない。

- Data プラットフォーム / ETL（src/kabusys/data/）
  - calendar_management:
    - JPX カレンダー取得／営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - market_calendar 未取得時は曜日ベース（平日を営業日）でフォールバック。
    - カレンダーの夜間差分取得ジョブ（calendar_update_job）を実装。バックフィル・健全性チェックを含む。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl へ再エクスポート）。
    - ETL パイプラインの主要設計（差分更新、冪等保存、品質チェックの収集・継続処理）を実装方針として含む。
    - 品質チェック（quality モジュール）で重大度の問題が検出されても ETL 自体は継続し、呼び出し側で判断可能。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Security
- API キー（OpenAI 等）は環境変数経由で読み込む設計。Settings の各必須プロパティは未設定時に ValueError を発生させるため、アプリ実行前に環境を正しく設定すること。
- ログに機密トークンを出力しない実装を前提（コード内にトークン出力箇所は含まれていません）。運用時はログ設定に注意してください。

### Notes / Known limitations
- OpenAI 依存:
  - news_nlp / regime_detector ともに OpenAI のレスポンスを前提とするため、API キー未設定時は ValueError を送出します。
  - API エラー時はフェイルセーフとして対象スコアを 0.0（またはスキップ）にして継続する設計です（例: macro_sentiment=0.0）。
- .env 自動読み込み:
  - プロジェクトルート検出は .git または pyproject.toml を基準にしているため、配布形態や実行環境によっては自動検出されず手動で環境変数を設定する必要があります。自動読み込みの無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- DuckDB 互換性:
  - DuckDB の executemany に空リストを渡せないバージョン（0.10 系）に対応するため、空チェックを行っています。将来の DuckDB バージョンでは不要になる場合があります。
- ルックアヘッドバイアス回避:
  - AI / 研究モジュールは明示的に date 引数を受け取り、内部で date.today() や datetime.today() を参照しない設計になっています（バックテストでのルックアヘッド回避）。
- 部分書き込み保護:
  - AI スコアの DB 書き込みは対象コードのみを削除して差し替える方式（DELETE → INSERT）を採用。これにより一部チャンク失敗時に既存データを保護します。

---

今後のリリースでは、API クライアントの抽象化、監視/実行モジュールの実装詳細、strategy と execution の連携機能（注文実行フロー・手数料・ポジション管理）などを予定しています。