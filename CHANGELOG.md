CHANGELOG
=========

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - YYYY-MM-DD
------------------
初回リリース

Added
- パッケージ初期構成を追加
  - パッケージメタ情報: kabusys v0.1.0（src/kabusys/__init__.py）
  - 公開モジュール: data, strategy, execution, monitoring（__all__）

- 環境設定管理（kabusys.config）
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に検索し、.env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサ実装: export 形式対応、シングル／ダブルクォート内のエスケープ処理、行内コメント処理などに対応。
  - 環境変数保護（OS 環境変数の上書き制御）と override ロジック。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 実行環境等の設定をプロパティ経由で取得。入力値検証（KABUSYS_ENV, LOG_LEVEL）とユーティリティプロパティ（is_live, is_paper, is_dev）を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を利用して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
  - ニュース収集ウィンドウ計算（JST 基準; 前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として実装。
  - バッチ処理（最大 20 銘柄 / コール）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - リトライ＆バックオフ（429・ネットワーク断・タイムアウト・5xx を対象）とレスポンス検証ロジック（JSON 抽出、results 構造検証、型チェック、±1.0 クリップ）。
  - DuckDB への冪等書き込み（DELETE→INSERT）で部分失敗時に他銘柄データを保護。
  - テスト容易性のため _call_openai_api を差し替え可能に実装。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
  - prices_daily と raw_news を参照し、ma200_ratio 計算、マクロ記事フィルタ、LLM 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
  - OpenAI 呼び出しのリトライ・エラー処理・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
  - ルックアヘッドバイアス防止の設計（date 未満のデータのみ使用、datetime.today() を参照しない）。
  - テストのため API 呼び出し関数をモジュール内で独立実装。

- 研究（research）モジュール
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の扱い（必要行数未満は None）や計算用のスキャン範囲バッファを考慮。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns: LEAD を用いた任意ホライズン対応）、IC（Spearman）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を標準ライブラリのみで実装。
    - パラメータ検証（例: horizons の妥当性）や ties の平均ランク処理。

- データ管理（data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）用ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックで一貫した判定を行う設計。
    - カレンダー夜間バッチ（calendar_update_job）による J-Quants 差分取得・バックフィル・健全性チェック・冪等保存を実装。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の集約、品質問題とエラーの記録、has_errors / has_quality_errors / to_dict）を実装。
    - ETL パイプライン方針とユーティリティ関数（テーブル存在チェック、最大日付取得など）の骨組みを提供（詳細 ETL ロジックは jquants_client/quality との連携前提）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス回避: AI スコアやファクター算出は内部で現在日時を直接参照せず、明示的な target_date を入力として扱う設計。
- フォールトトレランス: 外部 API（OpenAI / J-Quants）失敗時のフェイルセーフ（スコア 0.0 で継続、部分失敗時に DB の他データを保護）を重視。
- テスト性: OpenAI 呼び出しポイント（_call_openai_api）を差し替え可能にしてユニットテストやモックの導入を容易にしている。
- DuckDB 互換性注意: executemany に空リストを渡さない等、特定バージョンの DuckDB の挙動を考慮した実装。

既知の制限 / TODO
- strategy / execution / monitoring の詳細実装（パッケージ参照先には名前空間のみ定義されているが、本差分で示されたファイル群に含まれていない部分あり）。
- 一部の ETL 詳細や jquants_client / quality モジュールの具体実装に依存する箇所があるため、それらと統合する際の追加検証が必要。
- PBR・配当利回り等のバリューファクター拡張は未実装。

---

以降のリリースでは、API の安定化、追加ファクター、戦略モジュール（バックテスト・実行層）の詳細実装、監視・運用機能の充実を予定しています。