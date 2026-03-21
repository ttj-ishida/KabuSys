CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし（空）

[0.1.0] - 2026-03-21
--------------------

Added
- 初回リリース（ライブラリ版 v0.1.0）。
- パッケージのエントリポイントを追加。
  - kabusys.__init__.__version__ を "0.1.0" に設定し、公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理（kabusys.config）。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に自パスから探索。
  - .env / .env.local の自動読み込み（OS 環境変数を保護、.env.local は override）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パース強化: export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理、コメント判定の挙動。
  - 必須キー取得ヘルパー _require と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境名 / ログレベルなど）。
  - KABUSYS_ENV / LOG_LEVEL の値検証と is_live / is_paper / is_dev ヘルパー。
- データ取得・保存（kabusys.data.jquants_client）。
  - J-Quants API クライアントを実装。
  - レート制限管理（_RateLimiter、120 req/min 固定間隔スロットリング）。
  - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 時の自動トークンリフレッシュ（1 回のみ再試行）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT を用いた更新）。
  - レスポンスの型変換ユーティリティ（_to_float, _to_int）。
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアス対策に配慮。
- ニュース収集（kabusys.data.news_collector）。
  - RSS フィードから記事を収集し raw_news に保存する処理の骨格を実装（デフォルトでは Yahoo ビジネス RSS を設定）。
  - セキュリティを意識した実装方針:
    - defusedxml を用いて XML 攻撃を防御。
    - HTTP/HTTPS スキームの許可のみ、SSRF 対策方針を明記。
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）。
    - 記事 ID 生成に URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、断片削除、クエリソート）＋ SHA-256 を想定。
  - バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）などパフォーマンス配慮。
- 研究・ファクター計算（kabusys.research.*）。
  - ファクター計算モジュール（factor_research）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）。
    - Value（per, roe：raw_financials から最新財務データを取得）。
    - SQL と DuckDB ウィンドウ関数を用いた実装（データ不足時は None を返す）。
  - 特徴量探索（feature_exploration）:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、SQL による LEAD を使用）。
    - IC（Information Coefficient）計算（スピアマンの ρ をランクで計算、ties の平均ランク処理）。
    - factor_summary（count/mean/std/min/max/median の算出）。
    - rank ユーティリティ（同順位は平均ランク、丸めによる ties 検出対策）。
  - research パッケージの便利関数群を __all__ で公開。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）。
  - 外部 research モジュールの生ファクターを取得後、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - 正規化（zscore_normalize を利用）、Z スコアを ±3 でクリップ、features テーブルへ日付単位の置換（トランザクション）として保存（冪等）。
  - 価格参照は target_date 以前の最新価格を用いることで休場日や当日欠損に対応。
- シグナル生成（kabusys.strategy.signal_generator）。
  - features と ai_scores を統合して最終スコア final_score を計算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
  - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完して過度な降格を防止。
  - Bear レジーム検知（ai_scores の regime_score 平均が負でサンプル数閾値以上の場合に Bear と判定）により BUY を抑制。
  - BUY 生成閾値デフォルトは 0.60。BUY/SELL を算出後、signals テーブルへ日付単位で置換（トランザクション）。
  - エグジット判定（_generate_sell_signals）:
    - ストップロス（終値 / avg_price - 1 < -8%）優先。
    - final_score が閾値未満の場合は score_drop により SELL。
    - 価格欠損時は SELL 判定をスキップして誤クローズ防止。
  - weight 引数の妥当性検査・補正（未知キー・非数値・負値は無視、合計が 1.0 でない場合は再スケール）。
  - SELL を優先して BUY ランクを再付与する方針。
- データ統合・ユーティリティ
  - zscore 正規化ユーティリティは kabusys.data.stats から提供して利用（参照実装あり）。
  - DuckDB を前提とした SQL とトランザクション（BEGIN/COMMIT/ROLLBACK）処理を多用し、原子性を担保。

Changed
- なし（初期リリースにおける実装事項の列挙）。

Fixed
- なし（初期リリース）。

Security
- news_collector: defusedxml 使用、受信サイズ制限、トラッキングパラメータ除去、SSRF/スキーム検証方針等を明記。
- jquants_client: トークン再取得時の無限再帰防止（allow_refresh フラグ）、HTTP 429 の Retry-After 優先処理など堅牢化。

Notes / 実装上の設計判断（推測）
- Look-ahead Bias 回避のため、各処理は target_date 時点までにシステムが「知り得た」データのみを使用する設計になっている（fetched_at の記録、target_date 以前の最新価格参照など）。
- 冪等性を重視しており、DB への保存は ON CONFLICT / 日付単位の置換パターン（DELETE + INSERT）を採用。
- DuckDB を主要なローカル時系列ストアとして想定し、SQL ウィンドウ関数を活用して効率的に計算している。
- 一部の機能（トレーリングストップ、時間決済など）は実装留保（positions テーブルに追加情報が必要）として注記あり。

Known limitations / TODO（コード上に注記あり）
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装。
- 一部の入力検証（外部から渡される重みや AI スコアの取得方法）は実運用での追加検証が想定される。
- news_collector の完全実装（RSS パース・記事 ID 生成・DB 挿入・銘柄紐付け）は骨格があるが、詳細の実装が継続される想定。

―――

この CHANGELOG は、ソースコードのコメント・設計意図・関数名・定数・ログメッセージ等から推測して作成しています。実際の変更履歴やリリースノートと異なる場合があります。必要であれば、リリース日や項目の精度を合わせるために補足情報（コミットログ、リリースタグ）を提供してください。