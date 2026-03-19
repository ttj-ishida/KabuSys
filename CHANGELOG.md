# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このリポジトリのコードから推測できる機能追加・仕様・既知の制約を基に初回リリースの変更履歴を作成しました。

全般的な注意
- この CHANGELOG はソースコードのドキュメント文字列・実装から推測して作成しています。実際のリリースノートとして使用する場合は、リリース手順やパッケージ化時の変更点（依存関係、ビルド設定など）を合わせて確認してください。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初回公開リリース。日本株を対象とした自動売買システムのコア機能群（データ収集・保存、ファクター計算、特徴量生成、シグナル生成、環境設定ユーティリティ）を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期化（version = 0.1.0）。公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルート判定: .git または pyproject.toml を親ディレクトリから探索して自動検出。
    - 読み込み優先度: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途想定）。
  - .env パーサを実装:
    - 空行・コメント行のスキップ、export KEY=val 形式対応、シングル/ダブルクォート対応とエスケープ処理、インラインコメント処理を考慮。
  - Settings クラスを提供し、J-Quants トークンや kabu API パスワード、Slack トークン、DB パス等をプロパティ経由で取得。バリデーション（env 値や log level の許容値チェック）を実装。

- データ収集・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - 固定間隔のレートリミッタ（120 req/min）によるスロットリング。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx に対応。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（リフレッシュ失敗時は例外）。
    - ページネーション対応で全件取得。
    - 取得時に fetched_at を UTC ISO8601 形式で付与（Look-ahead バイアス追跡）。
  - DuckDB へ冪等的に保存する関数を実装:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT ... DO UPDATE（date, code を PK と想定）で保存。
    - save_financial_statements: raw_financials テーブルへ冪等保存（code, report_date, period_type を PK）。
    - save_market_calendar: market_calendar テーブルへ冪等保存。
    - データ変換ユーティリティ (_to_float, _to_int) を提供し、無効値や不正値を安全に None に変換。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集する基盤を実装（デフォルトに Yahoo Finance のビジネス RSS を登録）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - HTTP/HTTPS スキーム以外の URL を拒否する設計方針（SSRF 対策）。
    - 受信サイズ上限 MAX_RESPONSE_BYTES（10 MB）を設定しメモリ DoS を緩和。
  - URL 正規化機能を実装:
    - トラッキングパラメータ（utm_*, fbclid など）除去、スキーム/ホストの小文字化、フラグメント削除、クエリソート等。
    - 正規化後の URL の SHA-256 ハッシュ（先頭 32 文字）を記事 ID に使う方針（冪等性のため）。
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE=1000）を想定し、DB への負荷を抑制。

- リサーチ（研究）モジュール (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算。
    - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - calc_value: latest raw_financials を用いて PER, ROE を計算（price と組合せ）。
    - DuckDB の prices_daily / raw_financials テーブルのみ参照する、外部 API へはアクセスしない設計。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日の終値から各ホライズン（デフォルト [1,5,21]）先のリターンを計算（LEAD を用いた単一クエリ実装）。
    - calc_ic: スピアマンのランク相関（IC）を実装（ties は平均ランクで処理、サンプル 3 未満は None を返す）。
    - factor_summary: count/mean/std/min/max/median の統計サマリを返す。
    - rank: 同順位は平均ランクとするランク付けを提供。
  - zscore_normalize ユーティリティは kabusys.data.stats から提供（re-export）。

- 特徴量生成 (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research モジュールの生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - DuckDB の features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで実行し冪等性を担保）。
    - target_date 以前の最新価格を参照して価格欠損や休場日に対応。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features テーブルと ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - 重み（デフォルトは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）を受け付け、入力の検証・フォールバック・正規化（合計を 1.0 に再スケール）を行う。
    - AI スコアが未登録の銘柄は中立値（0.5）で補完。
    - Bear レジーム検知: ai_scores の regime_score の平均が負（かつサンプル数 >= 3）で BUY シグナルを抑制。
    - BUY シグナル閾値デフォルト 0.60、STOP-LOSS は -8%。
    - 保有ポジションに対する SELL シグナル判定を実装（ストップロス優先、スコア低下での売却など）。
    - signals テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで実行）。

### 変更 (Changed)
- 初期リリースのため該当なし（新規実装のみ）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- XML パースに defusedxml を使用し、RSS/ATOM の外部攻撃に配慮。
- news_collector では受信サイズ上限や URL スキーム制限を設け、メモリ DoS / SSRF リスクを軽減する設計。

### 既知の制約・未実装（注意事項）
- signal_generator の一部エグジット条件（トレーリングストップや時間決済）は未実装。positions テーブルに peak_price / entry_date が必要で、将来の実装予定。
- news_collector の実装コメントでは「INSERT RETURNING で実際に挿入されたレコード数を返す」とあるが、現行の実装は executemany/ON CONFLICT ベースでの保存が中心。実際の RETURNING の使用は DB 実装やドライバに依存するため、必要に応じて調整が必要。
- DuckDB のスキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）はコードが期待する形で事前に作成しておく必要がある。
- J-Quants API クライアントはネットワーク/認証に依存するため、実稼働時は JQUANTS_REFRESH_TOKEN といった必須環境変数の設定が必要（Settings は未設定時に ValueError を送出する）。

### 将来の改善案 / TODO（コード内コメントより）
- signal_generator:
  - トレーリングストップ、保有期間ベースの時間決済ルールを実装。
- news_collector:
  - URL 正規化・記事 ID 生成の検証と、より強固なデデュープ手続き（タイトル・本文類似度など）を検討。
- jquants_client:
  - 429 の Retry-After ヘッダ対応は実装済みだが、レート制御戦略（固定間隔以外のトークンバケット等）の検討。
- テスト:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑止できるが、環境依存テストの整備が推奨。

---

参考: 各モジュールの主要エントリポイント
- kabusys.config: settings（Settings インスタンス）
- kabusys.data.jquants_client: get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector: ニュース取得/正規化ユーティリティ、および保存ロジック
- kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（再エクスポート）
- kabusys.strategy: build_features, generate_signals

（この CHANGELOG はコード記述の解釈に基づいて作成しています。実際のリリースノートとして使用する場合は、実行環境での動作確認とプロジェクト固有の配布手続きに従って調整してください。）