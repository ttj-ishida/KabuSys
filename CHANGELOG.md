CHANGELOG
=========

全般
----
この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードベースの内容から推測して作成した初回リリース（v0.1.0）の変更点を日本語で記載しています。

[Unreleased]
------------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-20
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - 概要: 日本株の自動売買システム向けのデータ収集、ファクター計算、特徴量生成、シグナル生成、研究ユーティリティを含む基盤ライブラリを提供。

- 環境設定管理 (kabusys.config)
  - .env ファイル / 環境変数読み込み機能を実装。プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local を順に読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサは "export KEY=..." 形式、シングル/ダブルクォート、インラインコメント、エスケープシーケンスに対応。
  - 環境変数保護（OS 環境変数優先）や override ロジックをサポート。
  - Settings クラスを提供し、必須設定の取得と妥当性検査（KABUSYS_ENV, LOG_LEVEL 等）を実施。
  - 主要な必須環境変数（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルトの DB パス:
    - DUCKDB_PATH = data/kabusys.duckdb
    - SQLITE_PATH = data/monitoring.db

- データ収集クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアント実装
    - 固定間隔のレートリミッタ（120 req/min）
    - 再試行ロジック（指数バックオフ、最大3回）。408/429/5xx をリトライ対象。
    - 401 発生時はトークン自動リフレッシュを 1 回実施して再試行（無限再帰を回避）。
    - ページネーション対応の取得関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - 取得データを DuckDB に冪等保存する関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - 保存は ON CONFLICT を用いた UPDATE（冪等）。
    - レスポンスの fetched_at を UTC で記録（ルックアヘッドバイアス対策）。
    - 型安全な変換ユーティリティ: _to_float, _to_int（不正値は None）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news 等へ保存する処理を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML 攻撃を回避。
    - 受信最大バイト数を制限（10MB）。
    - URL 正規化でトラッキングパラメータ（utm_* 等）を除去、スキーム検査により SSRF の抑止。
  - 記事ID を URL 正規化後の SHA-256（先頭32文字等）で生成して冪等性を確保。
  - バルク INSERT のチャンク化で DB への負荷を低減。

- ファクター計算（研究用） (kabusys.research.factor_research)
  - prices_daily / raw_financials を用いたファクター計算を実装:
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）
    - Volatility / Liquidity: atr_20, atr_pct, avg_turnover, volume_ratio（20日ベース）
    - Value: per, roe（直近の財務データを参照）
  - SQL ウィンドウ関数を活用し、営業日欠損等を考慮したロバストな取得を実装。
  - データ不足（ウィンドウが不足）の場合は None を返す設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で算出した生ファクターをマージ、ユニバースフィルタを適用し、Z スコア正規化（zscore_normalize を利用）して features テーブルに UPSERT（date 単位で置換）するワークフローを実装。
  - ユニバースフィルタ:
    - 最低株価 _MIN_PRICE = 300 円
    - 20 日平均売買代金 _MIN_TURNOVER = 5e8（5 億円）
  - 正規化対象カラムを ±3 でクリップして外れ値影響を抑制。
  - 処理はトランザクション + バルク挿入で原子性を保証（冪等）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成・signals テーブルへ日付単位の置換で保存（冪等）。
  - コンポーネントスコア:
    - momentum, value, volatility, liquidity, news（AI スコア）
  - デフォルト重みと閾値:
    - デフォルト重みはドキュメント（StrategyModel.md Section 4.1）に基づく（例: momentum 0.4, value 0.2, ...）
    - デフォルト BUY 閾値 = 0.60
  - Bear レジーム検出: ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数閾値あり）。
  - SELL（エグジット）判定:
    - ストップロス: 現在終値が平均取得価格から -8% 以下
    - スコア低下: final_score が threshold 未満
    - 価格欠損時の SELL 判定スキップや、features 欠損銘柄は final_score=0.0 扱いなど安全策を実装。
  - 重みの補完・正規化、不正な重みの警告ロギングを実装。
  - signals テーブルの書き込みはトランザクションで原子性を確保。

- 研究ユーティリティ (kabusys.research.feature_exploration)
  - 将来リターン計算 (calc_forward_returns): 翌日/翌週/翌月（デフォルト [1,5,21]）等のリターンを一括取得。
  - IC（Information Coefficient）計算 (calc_ic): Spearman の ρ をランク処理で算出。サンプル不足（<3）時は None を返す。
  - factor_summary: count/mean/std/min/max/median を計算。
  - rank: 同順位は平均ランクを割り当てる実装（浮動小数の丸め対策あり）。

- パッケージ初期化
  - kabusys.__init__ に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に公開。
  - strategy モジュールのエクスポート簡略化（build_features, generate_signals）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector は defusedxml を使用し XML インジェクション/DoS を軽減。
- URL 正規化とスキーム検査により SSRF リスク低減。
- J-Quants クライアントはトークン管理とリトライ制御を厳密に実装し、401 ハンドリングとログ記録を強化。

Notes / 既知事項
- DuckDB を前提とした設計（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等のスキーマが必要）。
- execution パッケージは初期状態で __init__.py だけが存在し、発注実装は別途必要（このリリースでは実行層への直接依存は持たない設計）。
- news_collector の RSS ソースはデフォルトで Yahoo Finance のビジネスカテゴリを参照する（DEFAULT_RSS_SOURCES）。
- 一部の高度なエグジット条件（トレーリングストップ、時間決済）は positions テーブルの追加フィールド（peak_price / entry_date 等）が未整備なため未実装。
- settings の env 値検証により、不正な KABUSYS_ENV / LOG_LEVEL 値は ValueError を送出する。

将来の改善案（想定）
- execution 層の実装（kabu ステーション連携を含む）と、発注ロジックの統合。
- AI スコアの算出・学習パイプラインの追加およびニュース記事と銘柄マッチング精度向上。
- パフォーマンス最適化（大量銘柄に対するバッチ処理、並列化）。
- テストカバレッジの拡張（特に API リトライ・エラー条件、.env パーサの境界ケース）。

ライセンス / 著者
- （ソースからはライセンス情報が取得できないため省略）

--- 

注: 本 CHANGELOG は提供されたコード内容に基づき推測して作成しています。実際のリリースノートやドキュメントと差異がある可能性があります。必要であれば実際に含めたい追加情報（実行手順、DB スキーマ、環境変数一覧、既知のバグ等）をお知らせください。