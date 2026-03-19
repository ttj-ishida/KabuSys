# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。主な追加点と設計上の注意事項は以下の通りです。

### Added
- パッケージ構成
  - kabusys パッケージの公開インターフェースを整備（data, strategy, execution, monitoring をエクスポート）。
  - バージョン番号を `__version__ = "0.1.0"` として設定。

- 設定管理 (kabusys.config)
  - Settings クラスによる環境変数ラッパーを実装（J-Quants トークン、kabu API、Slack、DB パス、実行環境等を取得）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env / .env.local の優先順位と上書き / 保護ロジックを実装（OS 環境変数を保護）。
  - .env パーサを強化: export プレフィックス対応、シングル/ダブルクォートのエスケープ、インラインコメント処理などに対応。
  - 環境変数による自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制御（120 req/min 相当）。
  - 冪等性のある DuckDB への保存（ON CONFLICT DO UPDATE）を実装（raw_prices / raw_financials / market_calendar）。
  - ページネーション対応の fetch 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - リトライ戦略（指数バックオフ、最大 3 回、HTTP 408/429/5xx をリトライの対象）。
  - 401 発生時にリフレッシュトークンで自動更新して 1 回リトライする仕組みを実装（トークンキャッシュあり）。
  - JSON デコードの失敗に対するエラー整備とログ出力。
  - 型変換ユーティリティ `_to_float` / `_to_int` により入力データの堅牢な処理を実装。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集基盤を実装（デフォルトに Yahoo Finance のカテゴリ RSS）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事 ID を SHA-256 で生成して冪等性を確保する方針を導入。
  - defusedxml を用いて XML 攻撃を防御、受信サイズ制限（最大 10MB）、HTTP スキームチェック等を実装。
  - DB へのバルク挿入をチャンク化してパフォーマンスと SQL 長制限に配慮。
  - raw_news / news_symbols 等への保存を想定した実装方針を記載（実装の一部は注釈として記述）。

- リサーチ機能 (kabusys.research)
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）など。
    - calc_volatility: 20日 ATR、atr_pct、20日平均売買代金、出来高比率等。
    - calc_value: PER/ROE の計算（raw_financials と prices_daily を組み合わせて取得）。
  - 特徴量探索・評価ユーティリティを実装:
    - calc_forward_returns: 任意ホライズンの将来リターン（複数ホライズンを一度に取得）。
    - calc_ic: スピアマンの rank 相関（IC）計算（同順位は平均ランクで処理）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）集計。
    - rank: 値リストを平均順位でランク付けするユーティリティ。
  - 外部ライブラリに依存せず、DuckDB のみを使う設計。

- 戦略（Strategy）レイヤ (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュールの生ファクターを統合して正規化（zscore_normalize を利用）。
    - ユニバースフィルタ（価格 >= 300 円、20日平均売買代金 >= 5 億円）を実装。
    - Z スコアを ±3 でクリップし、features テーブルへ日付単位で置換（トランザクションで原子性確保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換・欠損補完（中立値 0.5）・重み合成の実装（デフォルト重みは StrategyModel.md に準拠）。
    - weights のバリデーション・フォールバック・再スケール処理を実装。
    - Bear レジーム判定（AI の regime_score 平均が負）により BUY を抑制するロジックを実装。
    - エグジット（SELL）判定: ストップロス（-8%）や final_score が閾値未満の場合を判定。SELL を優先して BUY から除外するポリシー。
    - signals テーブルへ日付単位で置換（トランザクションで原子性確保）。
    - 使いやすさのため generate_signals は threshold / weights を引数で上書き可能。

- ロギング・エラーハンドリング
  - 各所で詳細な logger 呼び出しを追加（情報・警告・デバッグ・例外時のロールバック失敗警告など）。
  - DB 操作はトランザクション管理（BEGIN/COMMIT/ROLLBACK）で原子性を確保。

### Fixed / Robustness improvements
- データ保存系関数で PK 欠損行をスキップし、その件数を警告ログとして出力するようにした（save_daily_quotes / save_financial_statements / save_market_calendar）。
- API リクエストで JSON デコードに失敗した場合に原文を含むエラーメッセージを出力し調査を容易にした。
- レートリミッタやリトライ処理で再帰的トークンリフレッシュを防ぐため allow_refresh フラグを導入。
- 数値変換ユーティリティが不正な浮動小数（例: "1.9" を int に変換しない）を安全に扱うようにした。
- features/signal の処理において欠損や非有限値の扱いを厳密化（None / NaN / Inf の特殊処理）。

### Security
- RSS 解析に defusedxml を採用して XML ベースの攻撃（XML Bomb 等）を緩和。
- ニュース収集で受信サイズ制限を実装しメモリ DoS を防止。
- URL 正規化時にスキーム・クエリ検査を行い SSRF や想定外スキームを排除する方針を採用。
- J-Quants クライアントはトークンを明示的にキャッシュし、トークン取扱いの再帰を避ける安全設計。

### Notes / Known limitations
- execution パッケージはインポート可能だが具体的な発注ロジック（kabu ステーションへの発注処理等）はこのリリースでは未実装／薄め。戦略層は発注 API に依存しない設計になっている。
- 一部仕様（トレーリングストップや時間決済など）は positions テーブルの追加情報（peak_price / entry_date 等）が必要で、現時点では未実装として注記。
- feature_engineering は zscore_normalize を外部ユーティリティ（kabusys.data.stats）に依存する。該当実装はパッケージ内で提供されている前提。
- NewsCollector の記事 ID は設計方針に記載。実際の DB スキーマや紐付けロジックは運用に合わせて調整が必要。

### Breaking Changes
- なし（初回リリース）

---

ご要望があれば、各モジュールごとの変更点をより細かく分割したバージョン履歴や、将来のマイグレーション注意点（DB スキーマ変更時の移行手順など）を追記します。