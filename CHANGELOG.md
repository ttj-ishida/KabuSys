# CHANGELOG

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  
安定バージョン、API、動作仕様の変更はここに記載します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムのコアライブラリを公開します。主な追加機能・実装内容は以下のとおりです。

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring をパッケージレベルで公開

- 設定 / 環境変数管理（kabusys.config）
  - .env/.env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）
  - .env パーサ: export KEY=val、クォート内のエスケープ、インラインコメント処理、コメント行スキップ等に対応
  - 上書き制御: .env と .env.local のロード順序・override ポリシー、既存 OS 環境変数の保護機構
  - Settings クラス: J-Quants トークンや kabu API パスワード、Slack 設定、DB パス、環境種別（development|paper_trading|live）およびログレベル検証ロジック
  - 必須キー未設定時に ValueError を投げる _require 関数

- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアント実装
    - 固定間隔のレートリミッタ（120 req/min）
    - 再試行（指数バックオフ、最大3回）、HTTP 408/429/5xx に対応
    - 401 発生時のトークン自動リフレッシュを1回行い再試行
    - ページネーション対応で全ページを取得
    - レスポンス JSON のデコードエラーやネットワークエラーに対する明確なハンドリング
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB 保存関数（冪等保存）
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装
    - ON CONFLICT DO UPDATE によるアップサート、PK 欠損行のスキップとログ出力
    - fetched_at に UTC タイムスタンプを記録
  - ユーティリティ: 安全な型変換関数 _to_float, _to_int

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事収集し raw_news へ冪等保存するモジュールを実装
  - セキュリティ対策:
    - defusedxml を使用（XML Bomb 対策）
    - URL 正規化とトラッキングパラメータ除去（utm_*/fbclid 等）
    - HTTP/HTTPS スキームチェック、受信サイズ上限（10MB）など SSRF / DoS に配慮
  - 記事IDは正規化 URL の SHA-256（先頭32文字）を想定して冪等性を確保
  - バルク挿入時のチャンク処理で SQL 長・パラメータ数上限に対応

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe：raw_financials と prices_daily を結合）
    - 欠損データや十分な窓幅がない場合は None を返す安全な実装
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定 horizon (デフォルト [1,5,21]) に対する将来リターンの計算（DuckDB SQL）
    - calc_ic: スピアマン（ランク）相関で IC を計算、サンプル不足時は None を返す
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出
    - rank: 同順位がある場合は平均ランクを割り当てる実装（丸めによる ties 判定対策あり）
  - zscore_normalize は kabusys.data.stats から利用可能（re-export）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで算出した生ファクターを統合・正規化して features テーブルへ保存
  - 処理フロー:
    - calc_momentum / calc_volatility / calc_value を呼び出し統合
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - Z スコア正規化（対象列を指定）、±3 でクリップ
    - date 単位で DELETE→INSERT の置換により冪等性とトランザクション原子性を保証
  - 実装上の注意点: ルックアヘッドバイアス防止のため target_date 時点のデータのみを参照

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を組み合わせて最終スコア（final_score）を計算し BUY/SELL シグナルを生成
  - コンポーネント:
    - momentum, value, volatility, liquidity, news（デフォルト重みを定義）
    - _sigmoid, _avg_scores 等の変換ユーティリティ
    - value の per に対する正規化ロジック（per=20 → 0.5）
    - volatility は atr_pct の Z スコアを反転して扱う
  - Bear レジーム判定: ai_scores の regime_score の平均が負の場合に Bear と判定（サンプル閾値あり）
  - SELL（エグジット）判定:
    - ストップロス（終値/avg_price - 1 < -8%）を最優先
    - final_score < threshold のとき SELL
    - 保有銘柄で価格欠損時は SELL 判定をスキップ（誤クローズ防止）
    - トレーリングストップや時間決済は未実装（TODO）
  - BUY 生成:
    - threshold（デフォルト 0.60）以上を BUY 候補。ただし Bear レジーム時は BUY を抑制
    - weights はユーザ入力を検証して既定重みでフォールバック・正規化
  - signals テーブルへ日付単位で置換して書き込み（トランザクションで原子性保証）

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の未実装 / TODO（リリース時点）
- signal_generator の SELL 条件におけるトレーリングストップ（peak_price / entry_date が positions に必要）
- signal_generator の時間決済（保有日数による自動クローズ）未実装
- news_collector: RSS パース後の銘柄紐付け（news_symbols へのマッピング）実装は想定されているが、関連の具体的挿入処理は今後の追加予定
- その他、外部依存を用いない設計方針により Pandas 等を使った便宜的な処理は導入していない（将来的に optional 拡張を検討）

### セキュリティ
- RSS/XML パースで defusedxml を利用して XML 攻撃を緩和
- ニュース URL 正規化でトラッキングパラメータ除去、受信サイズ制限でメモリ DoS に対処
- J-Quants クライアントでのトークン取り扱いはキャッシュを使用しつつリフレッシュ時の再帰保護を実装

### 互換性 / マイグレーション
- 初回リリースのため互換性に関する移行ルールはなし

---

作者・保守者は、今後のリリースで未実装の exit ルールやニュースのシンボルマッピング、テストカバレッジ強化などの改善を予定しています。バグ報告・機能要望は issue を作成してください。