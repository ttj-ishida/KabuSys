# CHANGELOG

このプロジェクトは Keep a Changelog 準拠で変更履歴を管理します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべての変更はセマンティックバージョニングに従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
最初の公開リリース。日本株自動売買・データ基盤・リサーチ・ニュースNLP・レジーム判定の基礎機能を実装しました。

### 追加 (Added)
- パッケージの基本情報
  - kabusys パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 環境変数パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - 読み込み時の保護（既存 OS 環境変数は protected）および override ロジックを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - Settings クラスを追加し、主要な設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_* 系, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）をプロパティ経由で取得・バリデーション。

- データ関連 (src/kabusys/data/*)
  - ETL パイプラインのインターフェース ETLResult を追加（pipeline モジュールの再エクスポート）。
  - pipeline モジュール（ETL 実行結果クラス、ユーティリティ）を実装。差分更新・バックフィル・品質チェックを想定した設計。
  - マーケットカレンダー管理モジュールを追加（calendar_management.py）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が存在しない場合は曜日ベース（週末は休場）でフォールバックする一貫したロジックを実装。
    - calendar_update_job を実装し、J-Quants API から差分取得 → 冪等保存（ON CONFLICT 相当）する夜間バッチ処理の設計を用意。
    - 異常検知（将来日時の健全性チェックやバックフィル）の実装。

- 研究・ファクター群 (src/kabusys/research/*)
  - factor_research モジュール:
    - calc_momentum: 約1/3/6か月リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR・相対ATR・20日平均売買代金・出来高比率を計算。
    - calc_value: PER（EPS が 0/欠損時は None）、ROE を raw_financials と prices_daily から計算。
    - 各関数は DuckDB 接続（prices_daily / raw_financials）を受け取り、(date, code) キー形式の結果リストを返す設計。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン先の将来リターンを一括で取得（複数ホライズン対応、入力検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。十分な有効データがない場合は None を返す。
    - rank: 同順位は平均ランクにするランク化ユーティリティを実装（丸め誤差対策）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリー。

- ニュースNLP & レジーム判定（AI） (src/kabusys/ai/*)
  - news_nlp モジュール:
    - calc_news_window: ターゲット日向けのニュース収集ウィンドウ（JST 基準→UTC 変換）を実装。
    - score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメントスコアを取得し、ai_scores テーブルへ冪等的に保存する処理を実装。
    - バッチサイズ、トークン肥大対策（最大記事数/最大文字数）、API リトライ（429/ネットワーク/タイムアウト/5xx の指数バックオフ）などの堅牢化。
    - レスポンスのバリデーション（JSON 抽出、results キー、型チェック、未知コード無視、数値チェック）と ±1.0 でのクリッピングを実装。
    - 部分失敗時に既存スコアを保護するため、更新対象コードを限定して DELETE → INSERT を行う設計（DuckDB executemany の互換性考慮）。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む処理を実装。
    - マクロ記事は raw_news からマクロキーワードでフィルタ（最大件数制限）。OpenAI を用いて JSON レスポンスから macro_sentiment を取得。
    - API のフェールセーフ: API 失敗やパース失敗時は macro_sentiment=0.0 を使用（例外を上位に伝播しない）。
    - リトライ・バックオフ・5xx 判定を実装。レジームスコア合成および閾値に基づくラベル付け（閾値は定数化）。
    - DB 書き込みは冪等に行う（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- 実装上の設計方針・運用上の配慮
  - ルックアヘッドバイアス回避: 各種処理で datetime.today() / date.today() を直接参照せず、外部から target_date を渡す設計を採用。
  - フェイルセーフ: データ不足や外部 API 失敗時は中立値（例: ma200_ratio=1.0、macro_sentiment=0.0、スコア未取得のスキップ）で継続する方針。
  - OpenAI 呼び出しは各モジュールで独立した _call_openai_api 実装を持ち、ユニットテスト時に patch で差し替え可能。
  - DuckDB に関する互換性考慮（executemany に空リストを渡さない等）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 破壊的変更 (Removed / Deprecated)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- API キー・パスワード等の機密は環境変数経由で取得する設計（Settings._require により未設定時は明示的エラー）。
- .env 自動読み込み時に既存 OS 環境変数は保護（上書き防止）。必要に応じて .env.local で上書き可能。

### 既知の制限・注意点 (Known Issues / Notes)
- OpenAI SDK（openai パッケージ）および DuckDB がランタイム依存として必要。実行環境にインストールされていることを前提とします。
- news_nlp/regime_detector は OpenAI API の利用料が発生します。API キー（OPENAI_API_KEY）を必ず設定してください。
- calc_value は現時点で PBR・配当利回りを未実装。
- strategy / execution / monitoring パッケージは __all__ に含まれていますが、この差分で提供される関数群は主にデータ・研究・AI 側の基盤です。運用時の発注ロジック・監視ロジックは別途実装が必要です。
- DuckDB のバージョンによる微妙なバインド動作差異に配慮しているが、実運用前に接続先 DuckDB での動作確認を推奨します。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）の fetch/save 実装に依存します。API 呼び出し・保存処理が環境に合わせて実装されている必要があります。

---

開発・運用に関する詳細は各モジュールの docstring と設計メモを参照してください。今後のリリースでは strategy（発注戦略）、execution（注文実行）および monitoring（アラート/監視）の実装強化、テストカバレッジ向上、及びパフォーマンス最適化を予定しています。