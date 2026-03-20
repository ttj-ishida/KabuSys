CHANGELOG
=========
すべての注目すべき変更点をここに記載します。  
本ファイルは「Keep a Changelog」形式に準拠します。

[Unreleased]
------------
（現在のスナップショットに未リリースの変更はありません）

[0.1.0] - 2026-03-20
-------------------
初回リリース。日本株自動売買プラットフォーム "KabuSys" の基礎機能を実装しました。
主な追加点は以下の通りです。

Added
- パッケージ初期化
  - kabusys パッケージを導入し、__version__ = "0.1.0" を設定。
  - パブリックサブパッケージとして data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（読み込み優先度: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
  - プロジェクトルート検出を .git または pyproject.toml から行う実装で、CWD に依存しない安定した動作を実現。
  - .env のパーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理などに対応。
  - Settings クラスを導入し、必須環境変数の検証（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）、既定値（API Base URL・DB パス等）、環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）を提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価・財務・マーケットカレンダー取得用のクライアントを実装。
  - レート制限対応: 固定間隔スロットリングで 120 req/min を厳守する RateLimiter を導入。
  - 再試行ロジック: 指数バックオフ（最大 3 回）とステータスコードベースの再試行ポリシー（408/429/5xx）。
  - 401 レスポンス時にはリフレッシュトークンを用いた id_token 自動更新（1 回のみ）を実装。
  - ページネーション対応（pagination_key の追跡）。
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE により冪等性を確保。
  - データ型変換ユーティリティ（_to_float / _to_int）を実装し、不正な型や空値に安全に対処。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news へ保存する基盤を実装（デフォルトで Yahoo Finance のビジネス RSS を登録）。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid, gclid 等）の除去、クエリのソート、フラグメント削除、スキーム/ホストの小文字化等を実施。
  - セキュリティ考慮: defusedxml を利用した XML パース、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）などを設計に反映。
  - 冪等保存のための記事 ID を URL 正規化後のハッシュで生成する方針（実装に必要な署名・保存処理を含む設計）。

- 研究用ファクター計算（kabusys.research.*）
  - factor_research モジュール:
    - モメンタム: calc_momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - ボラティリティ/流動性: calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - バリュー: calc_value（per, roe）（raw_financials から最新レコードを参照）
    - DuckDB の prices_daily / raw_financials を用いた SQL ベースの計算実装。
    - データ不足時（ウィンドウ内の行数不足など）は None を返す設計。
  - feature_exploration モジュール:
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、返却は fwd_1d/fwd_5d/fwd_21d 等）
    - IC 計算: calc_ic（Spearman の ρ、サンプル不足時は None）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - ランキングユーティリティ: rank（同順位は平均ランクで処理）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research 側で算出した生ファクターを読み込み、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で削除→挿入（トランザクション + バルク挿入）を行い冪等性を保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントスコアはシグモイド変換や逆スコア変換（PER 等）を適用。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（BUY: 0.60）を採用。ユーザー指定の weights は妥当性検査の上で正規化してマージ。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、ただしサンプル数閾値あり）では BUY シグナルを抑制。
    - エグジット（SELL）判定: ストップロス（終値 / avg_price - 1 < -8%）およびスコア低下（final_score < threshold）。保有銘柄の価格欠損時は SELL 判定をスキップして安全性を高める。
    - signals テーブルへ日付単位で削除→挿入（トランザクション + バルク挿入）を行い冪等性を保証。
    - BUY と SELL の優先ルールを実装（SELL 対象は BUY から除外し、ランクを再付与）。

- パッケージ API エクスポート
  - strategy.__init__ で build_features, generate_signals を公開。
  - research.__init__ で主要な解析ユーティリティ（calc_momentum 等、zscore_normalize を含む）を公開。

Security
- 外部データ取得部分においてトークン管理・自動リフレッシュ、受信サイズ制限、defusedxml の利用などのセキュリティ対策を導入。

Notes / Implementation details
- DuckDB を中心に SQL ウィンドウ関数を多用した実装とし、処理の再現性と高性能な分析を両立。
- 研究モジュールは外部ライブラリ（pandas 等）に依存しない設計。
- execution パッケージはインターフェースの準備のみ（初期リリースでは発注層の実装は含まれていません）。
- 一部のユーティリティ（zscore_normalize 等）は kabusys.data.stats から提供され、strategy / research モジュールで利用されています。

Deprecated
- なし

Removed
- なし

Fixed
- 初回リリースのため特定の「修正」はなし。

Security
- news_collector と J-Quants のクライアント周りで意図的にセキュリティ対策を盛り込んでいます（XML の安全パース、SSRF 想定の入力検証、受信サイズ制限、トークン管理）。

今後の予定（候補）
- execution 層の実装（kabuステーション等への接続と発注制御）。
- monitoring / observability 機能の拡充（Slack 通知など）。
- feature pipeline の検証・ユニットテストの強化。
- news_collector の記事→銘柄マッチングロジックの強化（news_symbols 保存処理の詳細実装）。
- トレーリングストップや時間決済など、SELL 条件の追加（現状は未実装の旨をコード内コメントで明記）。

---
この CHANGELOG はコードベース（src/ 以下）から実装内容を推測して記載しています。実際のリリースノートとして使用する場合は、変更点の確定とレビューを推奨します。