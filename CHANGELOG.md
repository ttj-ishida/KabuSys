# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。以下はコードベースから推測した主要な追加点・設計上の特徴です。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョン定義（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開APIの __all__ 設定（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能。
  - 読み込み優先順: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を検索）により CWD に依存しない読み込み。
  - 柔軟な .env パーサ（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントルール）。
  - 環境変数読み込み時の保護機能（OS 環境変数を protected として .env.local で上書きしない挙動）。
  - Settings クラスにより型付きプロパティを提供:
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）などの設定取得。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - is_live / is_paper / is_dev のヘルパープロパティ。
  - 必須環境変数未設定時は ValueError を送出する _require() 実装。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制御（120 req/min）。
  - リトライ（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After 優先、408/429/5xx を再試行対象に含む。
  - 401 Unauthorized を検知した場合はリフレッシュトークンで ID トークンを自動更新して一度だけ再試行。
  - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数（株価・財務・マーケットカレンダー）。
  - DuckDB への保存関数（save_daily_quotes/save_financial_statements/save_market_calendar）を実装。ON CONFLICT による冪等保存。
  - レスポンス値を安全に float/int に変換するユーティリティ (_to_float, _to_int) を提供。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集の基礎実装（デフォルトソースに Yahoo Finance のビジネス RSS）。
  - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
  - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）によるメモリDoS対策。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリキーソート）。
  - 記事 ID を正規化 URL の SHA-256 （先頭 32 文字）で生成し冪等性を確保。
  - SSRF 対策や危険なスキームの排除、DB へ ON CONFLICT DO NOTHING による冪等保存、バルク挿入のチャンク化。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR（true range を厳密に計算）、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の報告日ベース）。
    - 各関数は DuckDB の prices_daily/raw_financials テーブルのみを参照し、本番発注系には影響なし。
    - データ不足に対する安全な None 処理。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）を一括で取得。horizons の検証。
    - calc_ic: Spearman のランク相関（IC）計算。ties に対して平均ランクを採用し、サンプル不足時は None を返す。
    - rank, factor_summary 等の統計ユーティリティ（外部ライブラリに依存せず純粋 Python 実装）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで計算した生ファクターを取得して合成・正規化。
  - ユニバースフィルタを実装（株価 >= 300 円、20 日平均売買代金 >= 5 億円）。
  - Z スコア正規化適用（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
  - features テーブルへの日付単位の置換（削除→挿入）をトランザクションで原子性を保証（冪等）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ保存。
  - スコア計算:
    - momentum/value/volatility/liquidity/news の重み付き合算（デフォルト重みを実装）。
    - 各コンポーネントはシグモイド変換や逆転（ボラティリティ）等を適用。
    - None のコンポーネントは中立値 0.5 で補完して過度な降格を防止。
  - 重みはユーザ指定で上書き可能だが、検証（数値性/非負/有限）を行い合計を 1 に正規化する。
  - Bear レジーム検知機能（ai_scores の regime_score 平均が負の場合に BUY を抑制、サンプル数閾値あり）。
  - エグジット判定（SELL）:
    - ストップロス（終値/avg_price - 1 < -8%）を最優先。
    - final_score が閾値未満の場合に SELL。
    - 価格欠損時は SELL 判定をスキップしてログ出力（誤クローズ防止）。
  - signals テーブルへの日付単位置換をトランザクションで実行（冪等）。
  - generate_signals は BUY + SELL の合計シグナル数を返す。

### 修正 (Fixed)
- トランザクションエラー時のロールバック失敗を警告ログで通知する安全策を導入（feature_engineering / signal_generator の例外処理）。
- J-Quants API 呼び出しの JSON デコード失敗やネットワークエラーに対して分かりやすい例外メッセージを整備。

### セキュリティ (Security)
- RSS パーサに defusedxml を採用し XML 関連攻撃を軽減。
- ニュース収集で受信サイズ制限や URL 正規化、トラッキングパラメータ除去を実装。
- .env 読み込みで OS 環境変数を保護する protected 機能（.env.local が OS 環境変数を上書きしない）。

### ドキュメント / 設計ノート (Documentation / Design)
- 各モジュールに設計方針・処理フロー・注記を詳細にドキュメント化（コード内 docstring）。
  - ルックアヘッドバイアス防止の方針（target_date 時点のデータのみ使用）。
  - 本番発注層への非依存設計（strategy 層は execution 層に依存しない）。
  - DuckDB を中心としたデータフロー設計。

### 既知の制限・今後の実装予定
- signal_generator のエグジット条件ではトレーリングストップや時間決済（保有 60 営業日超）などが未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の詳細な URL/IP ベリフィケーションや外部ネットワークの厳格な SSF/ACL 制御は今後拡張の余地あり。
- 一部の数値処理でパフォーマンス最適化や大量データ時のバッチ戦略が今後の改善点。

---

謝辞:
- 初版ではデータ取得・加工・シグナル生成の中心機能を実装し、設計上の安全性（冪等性・例外処理・レート制御・入力検証）に配慮しています。今後は execution（発注）層やモニタリング/バックテストの拡充が想定されます。