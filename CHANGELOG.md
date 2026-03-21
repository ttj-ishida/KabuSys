CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

(現在未リリースの変更はありません)

[0.1.0] - 2026-03-21
-------------------

Added
- パッケージ初期リリース。基本構成と主要機能を実装。
- 公開 API / パッケージ構成
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
  - パブリックサブモジュールのエクスポート: data, strategy, execution, monitoring
  - strategy モジュールから build_features, generate_signals を公開

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト時に利用可能）。
  - .env パーサの強化:
    - コメント行の無視、export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしのインラインコメント判定（直前が空白/タブの場合のみ）
  - 読み込み順: OS 環境 > .env.local（override=True）> .env（override=False, OS 環境保護）
  - Settings クラスで各種必須設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, Slack トークン等）を取得・検証
  - 環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）検証とユーティリティプロパティ（is_live / is_paper / is_dev）

- データ取得・永続化 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装
    - API 呼び出しの固定間隔レートリミッタ（120 req/min）を実装
    - リトライロジック（指数バックオフ、最大 3 回）と 408/429/5xx 対応
    - 401 レスポンス時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ
    - ページネーション対応の fetch_* 関数 (fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar)
    - JSON デコード失敗時の明示的エラー
  - DuckDB への保存ユーティリティ
    - save_daily_quotes / save_financial_statements / save_market_calendar：冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）
    - PK 欠損行のスキップとログ出力
    - fetched_at を UTC ISO8601 で記録
  - ヘルパー: 安全な型変換 _to_float / _to_int

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集モジュールを実装（デフォルトで Yahoo Finance のビジネス RSS を指定）
  - セキュリティ・堅牢性の考慮:
    - defusedxml を利用して XML 攻撃を防止
    - 最大受信バイト数制限（10MB）でメモリ DoS を緩和
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）
    - 記事ID を正規化 URL の SHA-256 ハッシュで生成して冪等性を保証
    - SSRF 対策（HTTP/HTTPS スキーム以外を拒否する設計を想定）
  - バルク INSERT チャンク処理、トランザクションまとめなどパフォーマンス配慮

- 研究用ファクター算出 (src/kabusys/research/factor_research.py)
  - モメンタム calc_momentum:
    - mom_1m / mom_3m / mom_6m（LAG に基づく）と ma200_dev（200日移動平均乖離）
    - データ不足時は None を返す
  - ボラティリティ/流動性 calc_volatility:
    - ATR（20日）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算
    - true_range の NULL 伝播により過小評価を防止
  - バリュー calc_value:
    - latest raw_financials（report_date <= target_date）と当日の株価から PER, ROE を算出
    - EPS が 0/欠損 の場合 PER は None
  - 全関数とも prices_daily / raw_financials のみ参照、外部 API に依存しない設計

- 研究支援ユーティリティ (src/kabusys/research/feature_exploration.py)
  - 将来リターン calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）のフォワードリターンを一括取得
  - Information Coefficient（IC） calc_ic: factor と forward return の Spearman ランク相関を実装（サンプル数不足時は None）
  - ランク変換 rank（同順位は平均ランク、浮動小数丸めで ties の誤検出を防止）
  - factor_summary: count/mean/std/min/max/median を計算する統計サマリー

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features を実装:
    - research の calc_momentum / calc_volatility / calc_value を統合して features を構築
    - ユニバースフィルタ：最低株価 300 円、20 日平均売買代金 5 億円
    - 正規化: zscore_normalize を適用（対象カラムを指定）、±3 でクリップして外れ値影響を抑制
    - DuckDB の features テーブルへ日付単位で置換（削除→INSERT、トランザクションで原子性確保）
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ使用

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals を実装:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - スコア変換: Z スコア → シグモイド変換、欠損コンポーネントは中立 0.5 で補完
    - final_score は重み付き和（デフォルト重みを定義、入力重みは検証・正規化・スケーリング）
    - Bear レジーム判定: ai_scores の regime_score 平均が負で一定数以上のサンプルがある場合 BUY を抑制
    - BUY 生成は threshold=0.60 がデフォルト（パラメータで上書き可能）
    - SELL（エグジット）判定:
      - ストップロス: PnL <= -8%（優先）
      - スコア低下: final_score < threshold
      - 価格欠損やポジション情報欠如に対する安全対策（ログ出力とスキップ）
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）
    - SELL 優先ポリシー（SELL 対象は BUY から除外してランクを再付与）

Changed
- 設計方針・ドキュメントの反映: 各モジュールに設計方針・処理フロー・留意点を詳細に注釈として実装（look-ahead 防止、冪等性、トランザクション等）

Fixed
- （初期リリースのため Fixes はなし）

Security
- news_collector と XML パーシングに defusedxml を採用
- J-Quants クライアントでトークン更新やネットワークエラー時の安全なリトライを実装

Notes / Implementation details
- DuckDB を主要な一時/解析データストアとして使用。多くの DB 操作はトランザクションでラップして原子性を保証。
- 外部依存を最小化（research/feature_exploration は標準ライブラリのみを意図）。
- 一部機能は将来的な拡張を想定（例: signal_generator のトレーリングストップ・時間決済は positions テーブルの追加カラムが必要で未実装）。
- ロギングを各モジュールで行い、運用時の診断を支援。

----- 

参考: 本 CHANGELOG はコードベースから推測した実装内容に基づいて作成しています。実際のリリースノート作成時は、コミット履歴・差分・意図した公開 API を確認して適宜更新してください。