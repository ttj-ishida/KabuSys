# Keep a Changelog
すべての重要な変更はこのファイルに記録されます。  
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを使用します。

## [0.1.0] - 2026-03-20

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - モジュール公開: data, strategy, execution, monitoring を __all__ で指定。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
  - .env の読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを実装:
    - コメント行や空行を無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - インラインコメントの解釈はクォートの有無や直前のスペースに応じて安全に処理。
  - 環境変数保護機構: OS 環境変数を保護する protected セットを用いた上書き制御。
  - Settings クラスを実装し、アプリケーション固有の設定（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベル検証メソッドなど）を提供。env/log level の値検証（許可される値セット）を実装。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限制御（120 req/min 相当の _RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
    - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）と再試行の実装。
    - ページネーション対応で全件取得（pagination_key 利用）。
    - 取得タイミングを UTC で記録（fetched_at）してルックアヘッドバイアスのトレーサビリティを確保。
  - fetch_* 系関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（各ページネーション処理を含む）。
  - DuckDB への保存関数を実装（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
    - INSERT ... ON CONFLICT DO UPDATE を用いた冪等保存。
    - PK 欠損行のスキップ判定とログ出力。
    - レコードの型変換ユーティリティ (_to_float, _to_int)。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news へ保存する処理を実装（初期 RSS ソースに Yahoo Finance を含む）。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの正規化、フラグメント削除、クエリソート）を実装。
    - 記事 ID を正規化 URL の SHA-256 先頭 32 文字で生成して冪等性を保持。
    - SSRF/非 HTTP スキームの防止、バルク INSERT のチャンク化による DB 負荷対策。
  - raw_news への冪等保存と news_symbols 連携を想定した処理フロー。

- リサーチ系（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。データ不足時の None 処理。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新の財務レコードを銘柄ごとに取得）。
    - DuckDB SQL とウィンドウ関数を用いた効率的実装。営業日カバーのためのカレンダーバッファ考慮。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算実装（ペア不足時 None を返す）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで計算。
    - 決定的なランク処理（同順位は平均ランク）を行う rank ユーティリティ。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装:
    - research モジュールから生ファクターを取得しマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - zscore_normalize（kabusys.data.stats から利用）で正規化し ±3 でクリップ。
    - 日付ごとに features テーブルをトランザクションで置換（DELETE + bulk INSERT）して冪等性を保証。
    - 欠損価格・非有限値の扱いとログ出力を実装。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装:
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - momentum/value/volatility/liquidity/news のコンポーネントスコア計算（シグモイド変換、欠損は中立値 0.5 で補完）。
    - 重みのマージ・バリデーション・再スケーリング処理を実装（不正入力はスキップ、合計が 1.0 に補正）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負で一定サンプル数以上の場合）により BUY シグナル抑制。
    - BUY シグナル閾値デフォルト 0.60、BUY/Sell 生成ロジックを実装。
    - 保有ポジションのエグジット判定（ストップロス: -8% 以下、final_score が閾値未満）を実装。SELL 優先で BUY から除外。
    - signals テーブルへの日付ごとの置換をトランザクションで行い冪等性を保証。
    - ロギングと不整合時の警告出力を豊富に実装。

- パッケージの公開 API（src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py）
  - build_features, generate_signals, calc_momentum/calc_volatility/calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank を top-level にエクスポート。

### 変更
- なし（初期リリース）

### 修正
- なし（初期リリース）

### 既知の制限 / 未実装の機能
- signal_generator のエグジット条件のうち、トレーリングストップ（直近最高値から -10%）や長期保有時間による決済（60 営業日超）などは positions テーブルに peak_price / entry_date 等の情報が必要であり現バージョンでは未実装として注記されている。
- NewsCollector の具体的な RSS パース・DB 連携の一部詳細（news_symbols へのマッピング処理の完全な実装など）は将来的な拡張が想定されている。
- 外部依存（DuckDB テーブルスキーマ、Slack / kabuAPI の実働連携、J-Quants の実 API レスポンス仕様）に依存するため、運用前に環境変数設定・DB スキーマの整備・実 API キーの準備が必要。

### セキュリティ
- XML パースに defusedxml を利用し、RSS パース時の安全性に配慮。
- RSS 受信サイズ制限、URL 正規化、SSRF 想定対策を実装。

(注) 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。リリースノートには実際の運用での変更点・API 依存関係・DB スキーマ変更等を反映して適宜更新してください。