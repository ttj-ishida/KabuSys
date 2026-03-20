# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測した初回リリースの変更履歴です。

全般的な注記
- このリリースはパッケージバージョン 0.1.0（src/kabusys/__init__.py の __version__）に対応します。
- 多くの機能は DuckDB をデータ層として前提に実装されています。また本番の発注処理（execution 層）への直接依存は避け、戦略・データ収集・調査（research）モジュールは発注 API に依存しない設計です。

[Unreleased]
- （なし）

[0.1.0] - 2026-03-20
Added
- パッケージ初回リリース（kabusys 0.1.0）。
- 基本パッケージ構成とエクスポート
  - パッケージトップで data / strategy / execution / monitoring を __all__ として公開（src/kabusys/__init__.py）。
  - strategy と research 用の公開関数を __init__ で明示的にエクスポート（src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py）。
- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルート検出は .git または pyproject.toml を基準に行う（CWD 非依存）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 読み込み時に OS 環境変数を保護する保護セット（protected）をサポート。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントなどに対応。
  - Settings プロパティにより必須キーのチェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）や env/log_level の妥当性検査を実装。
  - デフォルトの DB パス（DuckDB / SQLite）や API ベース URL のデフォルト値を提供。
- データ取得・保存: J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API からのデータ取得関数を実装:
    - get_id_token: リフレッシュトークンから ID トークンを取得（POST）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: ページネーション対応で取得。
  - HTTP 層の堅牢化:
    - 固定間隔スロットリングによるレート制限遵守 (120 req/min) を RateLimiter で管理。
    - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx をリトライ対象）。
    - 401 応答時はトークン自動リフレッシュを行い 1 回リトライ（無限再帰防止フラグ）。
    - ページネーション間で ID トークンをモジュールレベルでキャッシュ。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。挿入は冪等（ON CONFLICT DO UPDATE）。
    - 日時は UTC の fetched_at を保持して Look-ahead バイアス追跡可能に。
    - 型変換ユーティリティ _to_float / _to_int により入力値の安全な正規化。
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集機能を実装（デフォルトの RSS ソースに Yahoo Finance を含む）。
  - セキュリティ・堅牢化:
    - defusedxml を使用して XML 攻撃を防御。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、メモリ DoS を軽減。
    - URL 正規化: トラッキングパラメータ（utm_*, fbclid 等）を削除、スキーム/ホストの小文字化、フラグメント削除、クエリソートを実施。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性確保。
    - HTTP/HTTPS 以外のスキームを拒否する等 SSRF 対策（コード内での検証を想定）。
  - DB 側ではバルク INSERT のチャンク処理、ON CONFLICT（DO NOTHING）や INSERT RETURNING による実際に挿入された件数の取得を想定。
- 研究（research）関連
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1m/3m/6m リターン、200日移動平均乖離（ma200_dev）を計算。十分なウィンドウがない場合は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播に配慮。
    - calc_value: raw_financials から直近財務データを取得し PER/ROE を計算（EPS=0 等は None）。
    - DuckDB のウィンドウ関数・集約を活用し効率的に実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）までの将来リターンを LEAD を使って一括取得。
    - calc_ic: スピアマンのランク相関（IC）を実装。ties は平均ランクで扱う。サンプル数が不足（<3）なら None。
    - factor_summary: 各ファクターに対する基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 丸めを使った同順位（ties）処理で平均ランクを返すユーティリティ。
  - research パッケージは上記ユーティリティをエクスポート。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value を利用して生ファクターを取得。
    - ユニバースフィルタ（最小株価 300 円、20日平均売買代金 >= 5億円）を適用。
    - 数値ファクターは zscore_normalize（kabusys.data.stats から提供）で正規化し ±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT をトランザクションで実施）して冪等性を保証。
    - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装:
    - features と ai_scores を読み込み、モメンタム/バリュー/ボラティリティ/流動性/ニュース の各コンポーネントスコアを計算。
    - コンポーネントスコアはシグモイド等で 0..1 に変換。欠損コンポーネントは中立値 0.5 で補完。
    - final_score を重み付き合算（デフォルト重みを実装）し、デフォルト閾値 0.60 で BUY シグナルを生成。
    - Bear レジーム判定（AI の regime_score 平均が負で、サンプル数閾値以上の場合）で BUY を抑制。
    - エグジット判定（売りシグナル）:
      - ストップロス: 実現損益率 <= -8% で即 SELL。
      - スコア低下: final_score が閾値未満なら SELL。
      - トレーリングストップや時間決済は未実装（注記あり）。
    - signals テーブルへ日付単位で置換（トランザクション＋bulk INSERT）。
    - weights 引数の検証・正規化（未知キーや非数値は無視、合計が 1 でない場合は再スケールもしくはデフォルトにフォールバック）。
- ロギングとデバッグ情報
  - 各主要処理は logger を使用して info/warning/debug を出力。処理件数や日付等のトレースが容易。

Security
- ニュース収集: defusedxml の採用や受信サイズ制限、URL 正規化により XML Bomb / SSRF / トラッキング排除 等を考慮。
- 環境変数の取り扱い: .env 読み込みはデフォルトで有効だが明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。OS 環境変数は保護され上書きされない。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Breaking Changes
- （初回リリースのため該当なし）

Notes / Limitations / TODO（コード内注記に基づく）
- execution 層（発注処理）はパッケージに存在するものの（src/kabusys/execution/__init__.py）、実装詳細はこのスナップショットでは含まれていない。
- signal_generator 内の一部のエグジット条件（トレーリングストップ・時間決済）は positions テーブルに peak_price / entry_date 等のカラムが必要で未実装。
- news_collector では「実際の HTTP フィード取得・パース・DB 挿入の詳細な実装」がコード断片末尾で途切れているため、実運用時は追加実装・検証が必要。
- zscore_normalize の実装本体は kabusys.data.stats に依存（このスナップショットでは該当ファイルの完全定義は含まれていない）。

以上。リリースノートはソースコードの docstring と実装から推測して作成しています。実際の変更履歴として使う場合はリポジトリのコミット履歴・リリース日付・責任者等で補完してください。