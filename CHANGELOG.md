# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
現在のパッケージバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-04

初回リリース — 日本株自動売買／データ基盤用のコアライブラリを提供します。

### Added
- 基本パッケージ情報
  - パッケージ初期化: kabusys.__version__ = 0.1.0、公開サブパッケージの __all__ を定義。

- 環境設定管理（kabusys.config）
  - .env ファイルと OS 環境変数の読み込みを自動で行う仕組みを実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - .env のパース機能を独自実装（コメント、export プレフィックス、クォート内のエスケープなどに対応）。
  - .env 読み込みの優先順: OS 環境変数 > .env.local（override=True）> .env（override=False）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - Settings クラスに多数のプロパティを実装（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境判定など）。
  - 環境変数値のバリデーション（KABUSYS_ENV、LOG_LEVEL の許容値チェック）と必須設定取得用の _require()。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブルの読み書き、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
    - DB にカレンダーがない場合の曜日ベースフォールバックを提供。最大探索日数制限で無限ループを防止。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック含む）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果・品質問題・エラーの収集と to_dict）。
    - ETL パイプライン設計（差分更新、保存、品質チェック、バックフィルの方針を反映）。
  - jquants_client と連携する設計（fetch/save を利用して idempotent にデータ保存）。

- AI（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を用いた銘柄別ニュース集約処理（前日 15:00 JST 〜 当日 08:30 JST のウィンドウを計算）。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出すバッチ処理を実装（最大バッチサイズ、1 銘柄あたりの文字制限）。
    - 再試行（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで処理。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ、部分成功時に既存スコアを保護するための個別 DELETE → INSERT ロジック。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - OpenAI 呼び出しのリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - DuckDB を用いたデータ取得と market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - 共通設計方針:
    - LLM 呼び出しはテスト時に差し替え可能（内部 _call_openai_api を patch 可能に設計）。
    - datetime.today()/date.today() を直接参照せず、ターゲット日を明示的に渡すことでルックアヘッドバイアスを防止。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）を DuckDB クエリで計算する関数を実装。
    - データ不足時の None ハンドリングや、営業日ベースのホライズン設計を実施。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等に依存しない純 Python 実装で、ties の処理や数値の有限性チェック等を行う。
  - data.stats からの zscore_normalize を再エクスポート（research パッケージ利用を簡便化）。

### Changed
- （初版のためなし）

### Fixed
- （初版のためなし）

### Security
- （現時点で報告なし）

### Notes / Implementation details
- 全体設計の共通方針として「本番の発注・口座情報にはアクセスしない」「DuckDB を用いたローカル分析基盤」「外部 API 呼び出しはフェイルセーフに」「ルックアヘッドバイアスの排除」を明示。
- OpenAI API は gpt-4o-mini を想定し JSON Mode を利用するプロンプト設計。レスポンスの堅牢なパースとバリデーションを重視。
- .env パーサはシェルライクな記法（export、クォート、インラインコメント）に対応するが、複雑なシェル展開（$(...), ``, 複数行クォート等）は想定外。
- DuckDB に対する executemany の注意（空リスト不可）や SQL の互換性を考慮した実装が含まれる。

---

今後のリリースでは、実運用向けの発注・実行モジュール（execution）、監視・アラート機能（monitoring）、さらなる品質チェック・メトリクスやテストカバレッジの追加が想定されます。