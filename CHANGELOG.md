# Changelog

すべての変更は Keep a Changelog の仕様に従い、重要な変更点のみを記載します。  
リリースのバージョンはパッケージ内の __version__ に合わせています。

## [0.1.0] - 2026-03-29

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（パッケージのトップ __all__）
- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）
  - .env パーサーの実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）
  - OS 環境変数保護（.env.local は override、.env は既存変数を上書きしない）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
  - Settings クラスによる設定プロパティ（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベル等）
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）、必須変数未設定時は ValueError を送出
- AI モジュール群 (kabusys.ai)
  - news_nlp: ニュース記事の銘柄別センチメント解析と ai_scores への書き込み
    - ニュース収集ウィンドウ計算（JST 基準）と DuckDB からの記事集約
    - OpenAI（gpt-4o-mini）の JSON モードを用いたバッチスコアリング（最大 20 銘柄 / チャンク）
    - リトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフ
    - レスポンス検証（JSON 抽出、results の検証、コード/スコアの検証、スコア ±1.0 クリップ）
    - DuckDB に対する冪等書き込み（DELETE → INSERT、executemany の空リスト回避）
    - テスト用フック: OpenAI 呼び出し関数をパッチ可能
  - regime_detector: 市場レジーム判定（ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM センチメントの合成）
    - ma200_ratio 計算（target_date 未満のデータのみ使用）とデータ不足時のフェイルセーフ（1.0）
    - raw_news からマクロキーワード抽出（最大件数制限）
    - OpenAI 呼び出し（リトライ/バックオフ、API エラー時は macro_sentiment=0.0 で継続）
    - レジームスコア合成と閾値判定（bull/neutral/bear）
    - market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）
    - テスト用フック: _call_openai_api を差し替え可能
- データプラットフォーム (kabusys.data)
  - calendar_management: JPX カレンダー管理・営業日判定・夜間更新ジョブ
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
    - market_calendar の有無に応じた DB 優先 or 曜日ベースのフォールバック設計
    - 最大探索日数制限で無限ループ防止
    - calendar_update_job: J-Quants から差分取得・バックフィル（直近再取得）・健全性チェックを実装
  - pipeline: ETL パイプライン公開インターフェース
    - ETLResult データクラス（取得件数・保存件数・品質問題・エラー等の集約）
    - 差分更新・バックフィル・品質チェック設計に沿った実装の土台
  - etl: pipeline.ETLResult の再エクスポート
- リサーチ用ユーティリティ (kabusys.research)
  - factor_research: ファクター計算（モメンタム / ボラティリティ / バリュー）
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離
    - calc_volatility: 20日 ATR・相対 ATR・平均売買代金・出来高比率
    - calc_value: PER / ROE（raw_financials から最新財務を取得）
    - DuckDB SQL を用いた実装（外部 API にはアクセスしない設計）
  - feature_exploration: 特徴量解析ユーティリティ
    - calc_forward_returns: 複数ホライズンの将来リターン取得（ホライズンは引数で指定）
    - calc_ic: スピアマンのランク相関（IC）計算（欠損や ties に対応）
    - rank: 平均ランクによるランク化（丸めで ties の安定化）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
- 各モジュールに詳細なロギング、フェイルセーフや入力検証を追加（運用時の観測性と安全性を向上）

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーの取り扱いは引数注入または環境変数参照に限定。キー未設定時は明示的に例外を返すことで誤動作を防止。

### 既知の注意点 (Known issues / Notes)
- DuckDB のバージョン差異に起因する executemany の空リスト問題へ対処済み（空リストチェックを実装）。ただし古い DuckDB の挙動により追加検証が必要となる場合がある。
- OpenAI 呼び出しはネットワーク状況や API 仕様の変更に依存するため、モックやテスト用差し替えを推奨。
- datetime.today()/date.today() の直接参照を避ける設計のため、関数呼び出し時に明示的な target_date を渡す運用を前提とする。

### 開発者向け（内部実装メモ）
- テスト容易性のため、OpenAI 呼び出しを行う内部関数に対して unittest.mock.patch による差し替えを想定した実装を行っている。
- .env パーサーは Bourne shell 風の export/コメント/クォート/エスケープをサポートしており、.env ファイルの柔軟な記述に耐える。
- market_regime / ai_scores など DB 書き込みは「DELETE → INSERT」の冪等パターンを採用している。

---

今後のリリース案（例）
- 0.2.0: 注文実行（kabu API）やモニタリング機能の実装、戦略モジュールの公開
- 0.2.x: ETL の完全化（品質チェックルール追加）、J-Quants クライアントの堅牢化

（本 CHANGELOG はコードベースの実装内容から推測して作成しています）