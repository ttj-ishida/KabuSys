# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載します。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを追加しました。主な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化（src/kabusys/__init__.py）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン 0.1.0 を定義。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込みを自動化（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env と .env.local の読み込み順序を実装（OS 環境 > .env.local > .env）。環境変数上書き制御（protected set）をサポート。
  - .env の行パーサを強化:
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - インラインコメントの取り扱い規則（クォート無し時の '#' の扱い）
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用可能）。
  - Settings クラスを実装（J-Quants トークン、kabuステーション設定、Slack トークン/チャネル、DB パス、環境判定、ログレベル検証など）。

- Data レイヤ（src/kabusys/data/*）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制御（固定間隔スロットリング）を実装（120 req/min の遵守）。
    - 再試行ロジック（指数バックオフ、最大 3 回。HTTP 408/429 および 5xx を対象）。429 の場合は Retry-After ヘッダを尊重。
    - 401 受信時にリフレッシュトークンで自動的に id_token を再取得して 1 回リトライ（無限ループ回避）。
    - ページネーション対応の取得関数（fetch_daily_quotes / fetch_financial_statements）を実装。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。fetched_at を UTC ISO8601 で記録し、ON CONFLICT による冪等性を担保。
    - 型変換ユーティリティ（_to_float / _to_int）を実装し、入力の堅牢性を向上。
  - ニュース収集（RSS）モジュール（src/kabusys/data/news_collector.py）
    - RSS 取得（fetch_rss）、前処理、ID 生成、DuckDB への冪等保存を提供。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリソート。
    - 前処理: URL 除去、空白正規化。
    - RSS の XML パースに defusedxml を使用して安全性を強化。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト先スキーム・ホスト検証（カスタム RedirectHandler）
      - ホスト名の DNS 解決結果を含めたプライベート IP 判定（ローカルネットワークへのアクセスを拒否）
    - レスポンスサイズ上限（デフォルト 10 MiB）と gzip 解凍後のサイズ検査を実装（DoS/Bomb 対策）。
    - バルク挿入のチャンク化（デフォルト 1000 件）とトランザクション管理。INSERT ... RETURNING を使用して実際に挿入された件数/ID を正確に返す。
    - 銘柄コード抽出ユーティリティ（4桁数字パターン）と news_symbols への紐付け処理を実装。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

  - DuckDB スキーマ定義（src/kabusys/data/schema.py）
    - Raw レイヤのテーブル DDL を追加:
      - raw_prices（生株価）
      - raw_financials（生財務データ）
      - raw_news（収集ニュース）
      - raw_executions（発注/約定用テーブルの DDL 断片を含む）
    - DataModel（Raw/Processed/Feature/Execution 層）に基づくスキーマ設計の骨子を実装。

- Research レイヤ（src/kabusys/research/*）
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）
      - DuckDB の prices_daily を参照して複数ホライズン（デフォルト: 1,5,21 営業日）の将来リターンを一度のクエリで取得。
      - ホライズン検証（正の整数かつ <= 252）やパフォーマンスのためのスキャン範囲制限を実装。
    - IC（Information Coefficient）計算（calc_ic）
      - ファクターと将来リターンを code で結合し、スピアマンのランク相関（ρ）を計算。十分なレコードがない場合は None を返す。
      - ties を平均ランクで処理するランク付けユーティリティ（rank）を提供。
    - ファクター統計サマリー（factor_summary）を実装（count/mean/std/min/max/median）。
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（calc_momentum）
      - mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）の計算を実装。必要なデータ不足時は None を返す。
    - ボラティリティ/流動性（calc_volatility）
      - 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
      - true_range の NULL 伝播制御やカウントによる十分データ判定を実装。
    - バリュー（calc_value）
      - raw_financials から target_date 以前の最新財務データを取得して PER（pclose/eps）と ROE を算出。EPS が 0/欠損の場合は None。
    - 研究モジュールの公開 API をまとめる __init__ を用意（calc_momentum/calc_volatility/calc_value/calc_forward_returns/calc_ic/factor_summary/rank と zscore_normalize をエクスポート）。

- その他
  - ロギングを多用し処理状況や警告を出力。
  - 外部依存は最小限（DuckDB と defusedxml のみ明示）。Research モジュールは pandas 等に依存しない設計。

### 修正 (Fixed)
- 初回リリースのため該当なし（設計段階での堅牢性・エラーハンドリングを実装）。

### セキュリティ (Security)
- ニュース収集で SSRF 対策を導入（スキーム検証、プライベート IP 判定、リダイレクト時の検査）。
- RSS パースに defusedxml を利用して XML による攻撃を軽減。
- J-Quants クライアントのトークンリフレッシュ時に無限再帰しない設計を導入。

### パフォーマンス (Performance)
- API 呼び出しのレートリミッタ実装により API 制限を順守。
- DuckDB へのバルク挿入をチャンク化してオーバーヘッドを削減。
- 一度の SQL で複数ホライズン/ウィンドウ集計を行うことでクエリ回数を削減。

### 既知の制限 (Known issues / Limitations)
- Research モジュールは pandas 等に依存していないため、非常に大規模データでは追加最適化が必要な場合があります。
- 一部機能（例: PBR・配当利回り）は現バージョンで未実装（calc_value の注記）。
- raw_executions の DDL がソース中で途中まで（ファイル末端が断片的）に見られます。今後のリリースで Execution 層の完全なスキーマを追加予定。
- Strategy / Execution / Monitoring の具体的な発注ロジック・kabuステーション連携は本リリースでは実装の土台を提供しており、実運用に用いる場合は追加実装と十分なテストが必要です。

今後の予定:
- Execution 層（kabuステーション連携・発注ロジック）の実装。
- Feature/Processed レイヤの ETL と定期バッチ処理。
- 単体テスト・統合テストの整備と CI ワークフロー導入。

---

注: 本 CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートはプロジェクト管理情報（コミット履歴・リリースノート）に基づいて補完してください。