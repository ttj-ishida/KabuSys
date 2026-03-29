# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  
リリース日付はソースコードから推測して付与しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システムのコアライブラリを提供します。主な機能・モジュールは以下のとおりです。

### Added
- パッケージ基盤
  - パッケージメタ情報と公開サブパッケージ定義を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - パッケージの公開 API に data, strategy, execution, monitoring を含める。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を実装。
  - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応）。
  - 既存 OS 環境変数を保護するための protected キーセットを尊重する上書きロジックを実装。
  - 必須環境変数を検査する _require() と Settings クラスを実装。J-Quants / kabu API / Slack / DB パス等の設定プロパティを提供。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。is_live / is_paper / is_dev の boolean プロパティを提供。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を基に、銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini, JSON mode）で評価し ai_scores テーブルへ保存する score_news を実装。
  - スコア付与用の時間ウィンドウ計算（JST 基準 → UTC naive datetime へ変換）を実装（calc_news_window）。
  - バッチ（最大 20 銘柄）での API 呼び出し、銘柄ごと記事数制限（最大 10 件）および文字トリム（最大 3000 文字）を実装。
  - エラー耐性設計：
    - 429、接続断、タイムアウト、5xx サーバーエラーに対する指数バックオフリトライ。
    - API/パース失敗時は該当チャンクをスキップして処理を継続（フェイルセーフ）。
  - レスポンスの厳密なバリデーション実装（JSON 抽出、results リスト検証、コード整合性、数値チェック、±1.0 クリップ）。
  - DuckDB への冪等保存（DELETE → INSERT、executemany を用いた個別 DELETE）およびトランザクション制御（BEGIN/COMMIT/ROLLBACK）。
  - 単体テスト容易化のため、OpenAI 呼び出し関数を patch で差し替え可能に設計。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出する score_regime を実装。
  - マクロニュース抽出、LLM への送信（gpt-4o-mini, JSON mode）、再試行・フォールバック（API 失敗時は macro_sentiment = 0.0）を実装。
  - レジーム合成ロジック（スコアのクリッピング・閾値設定）と market_regime テーブルへの冪等書き込みを実装。
  - テスト容易性のため、OpenAI 呼び出しを差し替え可能に設計。

- データ（src/kabusys/data）
  - ETL インターフェースの公開（src/kabusys/data/etl.py）として ETLResult を再エクスポート。
  - ETL パイプライン結果データクラス ETLResult と補助ユーティリティを実装（src/kabusys/data/pipeline.py）。
    - ETL の取得数・保存数・品質問題・エラー一覧を保持。has_errors / has_quality_errors プロパティと to_dict メソッドを提供。
    - 差分取得のためのテーブル最大日付参照、テーブル存在確認ユーティリティを実装。
    - デフォルトのバックフィル日数やカレンダー参照等の設計を反映。

  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定・次/前営業日取得・期間内営業日列挙・SQ 判定を実装。
    - DB にデータが無い場合は曜日（週末土日）ベースのフォールバックを採用。
    - calendar_update_job による J-Quants からの差分取得と冪等保存、バックフィル（日次で直近数日を再取得）・健全性チェック（過度に将来日付を検知した場合はスキップ）を実装。
    - 最大探索日数（探索範囲の上限）を設定して無限ループを防止。

- 研究用ユーティリティ（src/kabusys/research）
  - factor_research モジュール（calc_momentum, calc_volatility, calc_value）を実装：
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。データ不足は None。
    - Value: raw_financials から最新財務情報を取得して PER / ROE を計算（EPS が 0/欠損時は None）。
  - feature_exploration モジュール（calc_forward_returns, calc_ic, rank, factor_summary）を実装：
    - 将来リターンを一括で取得する SQL 実装（任意ホライズン対応、horizons の妥当性チェック）。
    - Spearman ランク相関（IC）計算。3 銘柄未満で計算不能な場合は None。
    - 平均・標準偏差・中央値等の統計サマリーを標準ライブラリのみで実装。
  - research パッケージの __init__ で主要関数を再エクスポート。

- find_project_root を用いたプロジェクトルート探索実装（config の .env 自動ロードに利用）。これによりカレントワーキングディレクトリに依存せずパッケージ配布後も正しく動作。

- OpenAI SDK（openai.OpenAI）を用いる全 AI 呼び出しで model=gpt-4o-mini, response_format={"type":"json_object"}, temperature=0, timeout=30 を指定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数自動読み込みで既存の OS 環境変数を上書きしないデフォルト動作と、保護されたキーセット（protected）を導入。
- 必須の秘密情報（API キー等）は取得できない場合に明確な ValueError を送出して早期失敗を誘導。

### Notes / Design decisions
- ルックアヘッドバイアス防止の観点から、すべての「日付基準処理」は datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を明示的に渡す設計。
- DuckDB を主要なオンディスクデータストアとして想定した SQL 実装。DuckDB のバージョン依存（executemany の空リスト制約やリストバインドの挙動）に配慮した実装を行っている。
- 複数箇所で外部 API 呼び出し（OpenAI / J-Quants）を行うが、フェイルセーフ設計（API 失敗時は部分処理継続）を採用。呼び出し部分はテストで差し替え可能。
- ai モジュールの一部関数（score_news）は kabusys.ai.__init__ で再エクスポート（score_news）。regime_detector は同パッケージに存在するが明示的な top-level 再エクスポートは行っていない（必要に応じて import して利用）。

---

今後のリリースでは、strategy / execution / monitoring の実装詳細（実際の発注ロジック、監視・アラート送信、バックテスト機能など）や、より細かな品質チェック・メトリクス集計、ドキュメント整備を予定しています。