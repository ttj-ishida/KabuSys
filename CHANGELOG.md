CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録します。
このファイルは日本語で記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-03-20
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ概要: 日本株自動売買システムの基礎モジュール群を提供。
  - エクスポート: data, strategy, execution, monitoring（execution は空パッケージ、monitoring は将来用に想定）。

- 環境設定 / 初期化（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない実装）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - .env パーサー実装:
    - コメント行・空行スキップ、export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い。
    - クォート無しの値では "#" の前が空白/タブの場合をコメントと認識。
  - Settings クラス:
    - J-Quants / kabu API / Slack / DB パス等のアクセサ（必須キーは未設定時に ValueError を送出）。
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）。
    - LOG_LEVEL の妥当性チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）とユーティリティプロパティ（is_live 等）。
    - デフォルトの DB パス（DuckDB / SQLite）を Path 型で返す。

- Data レイヤ（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - ページネーション対応の fetch_* 関数（株価日足, 財務データ, マーケットカレンダー）。
    - レート制限制御（120 req/min）を固定間隔スロットリングで実現する _RateLimiter を実装。
    - 再試行ロジック（最大 3 回、指数バックオフ、HTTP 408/429/5xx を対象）。
    - 401 Unauthorized を検出した場合、リフレッシュトークンにより id_token を自動更新して1回だけリトライ。
    - id_token のモジュールレベルキャッシュを導入（ページネーション呼び出し間で共有）。
    - JSON デコードエラーやネットワークエラーのハンドリング。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - 冪等性を担保する ON CONFLICT DO UPDATE 構文を利用。
      - PK 欠損行のスキップとスキップ数のログ警告。
      - fetched_at（UTC）を保存して取得時刻をトレース可能にする（Look-ahead バイアス防止設計）。
    - 入力変換ユーティリティ _to_float / _to_int を提供（不正値を None に変換）。

  - ニュース収集（kabusys.data.news_collector）
    - RSS フィードから記事を取得して raw_news に保存する処理を実装（DataPlatform.md に準拠）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストを小文字化、フラグメント除去、クエリソート）を実装。
    - 記事 ID は正規化 URL の SHA-256 先頭 32 文字で生成して冪等性を確保。
    - defusedxml を利用し XML Bomb 等の攻撃を緩和。
    - HTTP(S) スキーム以外の URL を拒否して SSRF を防止する方針を明記。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を導入してメモリ DoS を防止。
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE=1000）を導入。
    - INSERT RETURNING 相当（DuckDB 用に一括挿入後のログ）で実際に挿入された件数を報告。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を計算（DuckDB SQL ウィンドウ関数使用）。
    - volatility（atr_20, atr_pct, avg_turnover, volume_ratio）を計算（true_range の扱いに注意）。
    - value（per, roe）を計算（raw_financials の target_date 以前の最新財務レコードを結合）。
    - データ不足時に None を返すロバストな実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（horizons デフォルト [1,5,21]）を追加。
    - IC（Spearman の ρ）を計算する calc_ic（ランク変換・ties の平均ランク処理を含む）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）集計。
    - rank ユーティリティ（同順位は平均ランク、丸め処理で ties の検出漏れを防止）。

- Strategy（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research 側で算出した生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）を行い ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE → INSERT のトランザクション処理）し冪等性を確保。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を結合して momentum / value / volatility / liquidity / news コンポーネントを算出。
    - 各コンポーネントのスコア変換ユーティリティ（_sigmoid, _avg_scores 等）を実装。
    - final_score はデフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）で加重平均（ユーザー指定 weights を受け付け、検証・正規化して合計を 1.0 に整形）。
    - デフォルト BUY 閾値は 0.60。Bear レジーム判定（ai_scores の regime_score 平均が負の場合）時は BUY を抑制。
    - SELL（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 < -0.08（-8%）
      - final_score が threshold 未満（score_drop）
      - 価格欠損時は SELL 判定をスキップして誤クローズを防止
      - positions テーブルの情報が不足する一部条件（トレーリングストップ等）は未実装として明記
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- news_collector で defusedxml を使用し XML パーサ攻撃を防止。
- ニュース URL 正規化とスキーム制限で SSRF リスクを軽減。

Notes / 実装上の設計決定
- DuckDB を分析基盤に採用（価格・財務・features 等をローカル DB に保持）。
- 外部依存を最小化する設計（Research の分析ユーティリティは pandas 等に依存せず標準ライブラリ + DuckDB SQL による実装）。
- API クライアントはレート制限・リトライ・トークン自動更新・取得時刻取得（fetched_at）など自動化に重点を置き、Look-ahead バイアスの発生を抑制。
- 多くの DB 書き込みは冪等化（ON CONFLICT）および日付単位の置換（DELETE→INSERT をトランザクションで実行）により再実行可能性を担保。

今後の予定（未実装 / TODO）
- execution 層の発注実装（kabu API 経由）とモニタリング（monitoring）モジュールの実装。
- signals / positions に関する追加指標（peak_price / entry_date）を保存してトレーリングストップ等のエグジット条件を実装。
- News の記事→銘柄紐付けロジック（news_symbols）の精緻化、NLP ベースのスコアリング。
- 単体テスト・統合テストの整備と CI パイプライン。

--- 
リリースや変更に関する質問や、特定機能の詳細ドキュメント化（使用例、API 仕様、マイグレーション手順等）が必要であればお知らせください。