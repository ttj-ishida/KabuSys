Keep a Changelog
=================
すべての重要な変更点をここに記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。

履歴
----

### 0.1.0 - 2026-03-29
初回公開リリース。

Added
- パッケージ基盤
  - kabusys パッケージ初期化を追加。__version__ = 0.1.0 を設定。
  - パッケージ公開 API に data, strategy, execution, monitoring を想定（内部モジュールの整理を容易にするエクスポート定義）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート（テスト向け）。
  - .env パーサーを強化：export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理などに対応。
  - OS 環境変数を保護する protected 機能（.env の上書きを抑止）。
  - Settings クラスを追加して環境変数から安全に設定値を取得（必須キー検証、デフォルト値、値検証：KABUSYS_ENV, LOG_LEVEL）。
  - DB パス設定（DUCKDB_PATH, SQLITE_PATH）を Path として正規化。

- データ基盤 (kabusys.data)
  - カレンダー管理（calendar_management）を実装：
    - market_calendar を基にした営業日判定（is_trading_day）、前後営業日の取得（next_trading_day / prev_trading_day）、期間内営業日の列挙（get_trading_days）、SQ判定（is_sq_day）。
    - DB 未取得時の曜日ベースフォールバック（主に土日除外）。
    - 夜間バッチ更新ジョブ calendar_update_job（J-Quants API から差分取得・バックフィル・健全性チェック・冪等保存の実装）。
    - 安全な最大探索日数やバックフィル等の保護機構を導入して無限ループやデータ不整合を回避。
  - ETL パイプライン基盤（pipeline, etl）を実装：
    - ETLResult dataclass により ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化。
    - 差分取得・バックフィル・品質チェック想定のユーティリティを実装（テーブル存在確認、最大日付取得等）。
    - DuckDB の互換性を考慮した実装（executemany の空リスト回避等）。

- 研究・ファクター (kabusys.research)
  - factor_research モジュールを実装：
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）などの算出。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などの算出。
    - calc_value: raw_financials と組み合わせた PER / ROE 計算（target_date 以前の最新財務データを使用）。
    - DuckDB SQL を活用した高速な集合演算を採用し、外部 API へアクセスしない設計。
  - feature_exploration モジュールを実装：
    - calc_forward_returns: 任意ホライズンの将来リターンを一括で取得（ホライズンの検証あり）。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）計算。
    - rank / factor_summary: ランク変換、列ごとの基本統計量（count, mean, std, min, max, median）を提供。
    - 外部依存ライブラリに頼らない標準ライブラリ中心の実装。

- AI / ニュース解析 (kabusys.ai)
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で提供。
    - チャンク処理（最大20銘柄/回）、記事数・文字数のトリム、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ。
    - ネットワーク断・429・タイムアウト・5xx に対する指数バックオフリトライ、エラー時のフォールバック（失敗チャンクはスキップして継続）。
    - DuckDB への書き込みは部分的な置換（対象コードに限定した DELETE → INSERT）で部分失敗時のデータ保護を実現。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - regime_detector:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とニュース由来マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロ記事抽出（マクロキーワード一覧）→ LLM 評価（gpt-4o-mini）→ 合成スコア算出 → market_regime への冪等書き込みを実装。
    - API 失敗時は macro_sentiment=0.0 とするフェイルセーフ、リトライ・バックオフ・JSON パースの堅牢性を実装。
    - テスト用に _call_openai_api を差し替え可能に設計し、news_nlp とのモジュール結合を避けるため独立実装。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- .env 読み込みで OS 環境変数を保護する仕組みを導入（.env による意図しない上書きを防止）。
- OpenAI API キーは明示的に引数または OPENAI_API_KEY 環境変数から解決し、未設定時は明確なエラーを返す。

Notes / 設計上の注意
- すべてのモジュールはルックアヘッドバイアスを防ぐ設計（datetime.today()/date.today() を直接参照せず、target_date に基づく計算を行う）。
- 外部 API（OpenAI / J-Quants）での一時エラーは冗長にリトライするか、安全なデフォルト（スコア 0.0 やスキップ）で継続するフェイルセーフ思想を採用。
- DuckDB のバージョン互換性を配慮した実装（executemany の空リスト回避、リスト型バインドの回避など）。
- 本リリースでは strategy / execution / monitoring の具体的実装はパッケージ公開点検用に名前空間を確保しているが、個別実装は今後のリリースで追加予定。

将来の予定（抜粋）
- strategy / execution / monitoring の具体実装（バックテスト・発注ロジック・監視ジョブ）の追加。
- より細かな品質チェックルールや self-healing ETL の強化。
- OpenAI 呼び出しのロギング／コスト管理オプションの追加。

--- 
（注）この CHANGELOG はコードベースの実装内容から推定して作成しています。実際のリリースノートはパッケージの公式リリース記録に従ってください。