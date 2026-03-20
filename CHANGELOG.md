CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングに従います。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-20
-------------------

Added
- パッケージ初期リリース: kabusys (v0.1.0)
  - パッケージ公開情報:
    - バージョン: 0.1.0
    - パッケージトップで公開するサブパッケージ: data, strategy, execution, monitoring

- 環境設定 / 設定管理 (kabusys.config)
  - .env の自動読み込み機能を実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ の親ディレクトリ上で .git または pyproject.toml を探索（CWD 非依存）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能（テスト想定）
    - OS 環境変数のキーを保護する protected パラメータを用意し、override 時の上書きを防止
  - .env パーサを実装
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメントの扱い（クォート内は無視、クォート外は直前が空白/タブならコメントとみなす）
    - 無効行のスキップ
  - Settings クラスでアプリ設定をプロパティとして提供（環境変数から取得）
    - J-Quants / kabuAPI / Slack / DB パス（duckdb/sqlite）/ ログレベル / 実行環境フラグ等
    - 必須環境変数未設定時は明示的に ValueError を送出
    - KABUSYS_ENV / LOG_LEVEL の値検証（許可値を限定）

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装
    - 固定間隔スロットリングによるレート制御（120 req/min）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰回避）
    - モジュールレベルで ID トークンをキャッシュしてページネーション間で共有
    - レスポンス JSON のデコードエラーは明示的に RuntimeError を発生
    - fetch_* 系関数はページネーション対応
  - DuckDB への保存関数を実装（冪等）
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を利用して重複を排除
    - fetched_at は UTC 文字列で記録（Look-ahead バイアスのトレーサビリティ）
    - PK 欠損行をスキップし、スキップ数を警告ログ出力
    - 型変換ユーティリティ (_to_float / _to_int) を整備（安全な変換・不正値処理）
  - 内部 HTTP ユーティリティ (_request) にリトライ・429 の Retry-After 利用等の実装

- ニュース収集 (kabusys.data.news_collector)
  - RSS ベースのニュース収集モジュールを追加
    - デフォルト RSS ソース（例: Yahoo Finance）
    - 記事 URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）
    - defusedxml を使った XML パース（XML Bomb 等の防御）
    - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES、既定 10MB）でメモリDoS を防止
    - SSRF 対策や不正スキームの拒否等のセキュリティ配慮（設計方針）
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）やトランザクションの集約で DB オーバーヘッド削減
    - （設計メモ: 記事 ID を正規化 URL の SHA-256 ハッシュ先頭などで生成し冪等性を担保する仕様）

- 研究・ファクター計算 (kabusys.research)
  - factor_research: ファクター計算群を実装
    - モメンタム (calc_momentum)
      - mom_1m / mom_3m / mom_6m / ma200_dev を計算（ウィンドウサイズとスキャン範囲を実装）
      - 過去データ不足時に None を返す保護
    - ボラティリティ (calc_volatility)
      - 20 日 ATR（true_range の NULL 伝播を制御して正確に計算）、atr_pct、avg_turnover、volume_ratio
      - 必要行数未満は None を返す
    - バリュー (calc_value)
      - raw_financials の最新報告を結合して PER / ROE を算出（EPS が 0 または欠損時は None）
    - 実装方針: DuckDB の prices_daily / raw_financials のみ参照、本番 API に依存しない
  - feature_exploration: 分析ユーティリティを追加
    - calc_forward_returns: 将来リターン（指定ホライズン）の一括取得（単一クエリで効率よく）
    - calc_ic: スピアマンランク相関（IC）計算、サンプル不足時は None を返す
    - rank: 同順位は平均ランクとするランク付け（丸めによる ties 対応）
    - factor_summary: 各ファクター列の基本統計量（count / mean / std / min / max / median）
    - 設計方針: pandas 等に依存せず標準ライブラリ + duckdb で実装

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装
    - research モジュールから取得した生ファクターをマージしユニバースフィルタを適用
    - ユニバースフィルタ:
      - 株価 >= 300 円
      - 20 日平均売買代金 >= 5 億円
    - 指定列を Z スコア正規化（kabusys.data.stats:zscore_normalize を利用）、±3 でクリップして外れ値を抑制
    - 日付単位で features テーブルを置換（トランザクション + バルク挿入で原子性を保証）
    - 冪等性を意識した設計（target_date の既存行を削除してから挿入）

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news の各コンポーネントスコアを計算
    - コンポーネントスコア処理:
      - Z スコア → sigmoid 変換（0〜1）
      - PER に対する value スコアは 1 / (1 + per/20)（PER が小さいほど高スコア）
      - ボラティリティは反転シグモイド（低ボラ = 高スコア）
      - 欠損コンポーネントは中立 0.5 で補完し不当な降格を防止
    - weights のマージ・検証:
      - デフォルト重みを用意、ユーザ指定は既知キーのみ受け付け、合計が 1.0 になるよう正規化
      - 不正な重みはスキップして警告
    - Bear レジーム判定:
      - ai_scores の regime_score 平均が負 → Bear（ただしサンプル数閾値あり）
      - Bear の場合は BUY シグナルを抑制
    - BUY シグナル:
      - final_score が閾値（デフォルト 0.60）以上の銘柄を選択（Bear 時は抑制）
      - SELL 判定が出た銘柄は BUY から除外しランクを再付与（SELL 優先）
    - SELL シグナル（エグジット）:
      - 実装済みの条件:
        - ストップロス: 終値/avg_price - 1 < -8%
        - スコア低下: final_score < threshold
      - 価格欠損やデータ不足時の挙動: 価格欠損時は SELL 判定をスキップして警告、features に存在しない保有銘柄は final_score=0 と見なして SELL 対象にするログ
      - 未実装（設計メモ）:
        - トレーリングストップ（peak_price を使う）
        - 時間決済（保有日数ベース）
    - signals テーブルへの日付単位の置換（トランザクション + バルク挿入で原子性を保証）
    - ロギングにより処理結果を出力（BUY/SELL 数など）

Changed
- （初リリースのため過去からの変更はなし。設計上の注意点・制約をドキュメントとして明記）

Fixed
- （初リリースのため修正履歴はなし）

Security
- ニュース収集で defusedxml を使用し XML 攻撃に対処
- ニュース収集で受信サイズ制限を導入（メモリ DoS 防止）
- J-Quants クライアントで 401 時のトークンリフレッシュを安全に扱う（無限再帰回避）
- 環境変数読み込みで OS 環境変数の保護（protected set）を実装し意図せぬ上書きを防止

Notes / Design decisions
- 全体の設計方針:
  - 研究（research）コードと実行（execution）/発注層を厳密に分離し、ルックアヘッドバイアスを防止するために target_date 時点のデータのみを参照することを徹底
  - DuckDB を分析基盤として使用し、SQL と最小限の Python ロジックでファクター計算を行う
  - DB への保存は可能な限り冪等に（ON CONFLICT / 日付単位置換）して再実行可能性を確保
  - 外部ライブラリ依存を抑える（research モジュール等は pandas に依存しない実装）

今後の TODO / 機能案
- execution 層の実装（kabu API・注文送信ロジック）
- signals/positions 連携の強化（トレーリングストップ、保有日数ベースの時間決済）
- news_collector の記事→銘柄マッチング（news_symbols 登録処理）
- モニタリング・アラート機能（Slack 通知等）の追加

--- 

補足:
- 本 CHANGELOG はソースコードの内容から推測して記載しています。実際のリリースノート作成時はコミット履歴やリリース管理方針に合わせて調整してください。