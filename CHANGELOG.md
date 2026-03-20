# Changelog

すべての重大な変更をここに記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。  
現在の日付: 2026-03-20

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-20
初回リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - 公開 API: strategy.build_features, strategy.generate_signals、research の各ユーティリティ、config.settings。

- 環境設定/初期化（src/kabusys/config.py）
  - .env および .env.local からの自動読み込み機能（プロジェクトルートを .git / pyproject.toml から探索）。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env 行パーサ実装:
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォートとバックスラッシュエスケープの処理
    - コメント処理（クォート外での # の扱い）
  - 環境変数取得ユーティリティ（必須項目は未設定時に ValueError を送出）。
  - 設定プロパティ: J-Quants / kabu API / Slack トークン、DB パス（DuckDB/SQLite）、実行環境フラグ（development/paper_trading/live）、ログレベル検証等。

- データ取得 & 永続化（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装:
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - HTTP リトライ（指数バックオフ、最大 3 回、408/429/5xx を考慮）。
    - 401 応答時の自動トークンリフレッシュ（1 回）、モジュールレベルの ID トークンキャッシュを共有。
    - ページネーション対応（pagination_key を利用）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB 保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar（冪等化: ON CONFLICT DO UPDATE / DO NOTHING）。
    - fetched_at を UTC ISO 形式で記録。
    - 不完全レコード（PK 欠損）のスキップと警告ログ。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事登録機能（デフォルトに Yahoo Finance のカテゴリ RSS を含む）。
  - セキュリティ/堅牢化:
    - defusedxml による XML パース（XML Bomb 対策）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）。
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、クエリのキーソート、小文字化等）。
    - 記事 ID は正規化後 URL の SHA-256 の先頭を用いることで冪等性を確保。
    - HTTP/HTTPS スキーム以外を拒否する等の SSRF 脆弱性軽減を想定した設計。
  - DB 挿入はバルク（チャンク）で実施しパフォーマンスを考慮。

- 研究用ファクター計算（src/kabusys/research/*.py）
  - ファクター計算: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）。
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日 MA の乖離）。
    - Volatility: ATR（20日）、atr_pct、avg_turnover、volume_ratio。
    - Value: per（株価 / EPS）、roe（最新の報告書ベース）。
  - 特徴量探索・解析:
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）。
    - calc_ic（Spearman のランク相関による IC 計算）。
    - factor_summary（count/mean/std/min/max/median 計算）。
    - rank ユーティリティ（同順位は平均ランク）。
  - 外部ライブラリ（pandas 等）に依存せず、DuckDB と標準ライブラリで実装。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールから生ファクターを取得し、正規化・合成して features テーブルへ保存するパイプラインを実装。
  - ユニバースフィルタ:
    - 最低株価 300 円、20日平均売買代金 5 億円でフィルタリング。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
  - 日付単位での置換（DELETE + INSERT をトランザクションで実行し原子性を保証）。
  - ルックアヘッドバイアス防止の考慮（target_date 時点データのみ参照）。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を計算し、signals テーブルへ保存する処理を実装。
  - ファクター重み（デフォルト）と閾値:
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。
    - BUY 閾値デフォルト: 0.60。
    - 重みはユーザ指定を検証してマージ・再スケール。
  - コンポーネントスコア計算:
    - momentum/value/volatility/liquidity/news（AI スコアのシグモイド変換）を組み合わせ。
    - 欠損コンポーネントは中立 0.5 で補完。
  - Bear レジーム判定:
    - ai_scores の regime_score の平均が負の場合に Bear とみなし BUY を抑制。サンプル不足時は Bear とみなさない。
  - エグジット（SELL）判定:
    - ストップロス（終値/avg_price - 1 < -8%）を最優先。
    - final_score が閾値未満の場合は score_drop として SELL。
    - 価格欠損時の判定スキップや、features にない保有銘柄は score=0 として扱う等の安全措置。
  - 日付単位の置換で signals テーブルを更新（原子性を確保）。

- ユーティリティ
  - jquants_client の内部ユーティリティ: _to_float, _to_int（安全なパース）、_RateLimiter（最小間隔スロットリング）、堅牢な HTTP ハンドリング。
  - research/ranking・統計ユーティリティ（rank, factor_summary 等）。
  - strategy 層の各種数値変換と安定化処理（シグモイド、平均化、有効値フィルタなど）。

### Security
- RSS パーシングに defusedxml を利用し XML に関する攻撃を軽減。
- ニュース URL 正規化/スキーム制限などにより SSRF 等のリスクを低減。
- J-Quants クライアントはトークンリフレッシュ・キャッシュ・再試行制御を実装し、不正な認証状態を安全に扱う設計。

### Notes / Design Decisions
- 全体の設計方針として「ルックアヘッドバイアスを防ぐ」ことを重視。ほとんどの計算・判定は target_date 時点のデータのみを参照する。
- DuckDB をローカル分析基盤として用いる前提で SQL ウィンドウ関数等を多用。
- 発注/実際の execution 層との結合は持たず、戦略ロジックは signals テーブルへの出力に専念する設計になっている（execution パッケージは存在するが未実装/分離）。
- ロギングと警告を多用し、データ欠損や不正入力を検出して明示的にスキップまたは安全なフォールバックを行う実装。

### Known limitations / TODO（初期バージョンで未実装の項目）
- トレーリングストップや時間決済（保有 60 営業日超過）など一部のエグジット条件は未実装（ポジションテーブルに peak_price / entry_date が必要）。
- research の一部（PBR・配当利回りなど）は未実装。
- news_collector の外部ネットワーク/パースの詳しい堅牢化（証明書検査、接続タイムアウトチューニングなど）は今後強化可能。
- execution 層（発注・約定処理）は分離されており、実運用での接続実装が必要。

---

将来のリリースでは、execution 層の実装、追加ファクター（PBR 等）、モニタリング/アラート統合（Slack 連携など）および単体テスト・CI の整備を予定しています。