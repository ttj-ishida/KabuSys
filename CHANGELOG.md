# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]

## [0.1.0] - 2026-03-19
初期リリース。日本株自動売買システムのコア機能を実装しました。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報（0.1.0）と公開モジュール一覧を追加。

- 環境設定/読み込み
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。
    - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
    - .env と .env.local の優先順位制御、既存 OS 環境変数保護（protected set）をサポート。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ対応。
    - 必須設定取得ヘルパー _require と Settings クラスを実装（J-Quants / kabu / Slack / DB パス / 環境/ログレベル検証など）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と環境判定ユーティリティ（is_live 等）。

- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API 向け HTTP クライアント実装（ページネーション対応）。
    - レート制限を守る固定間隔スロットリング RateLimiter 実装（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回）と特定ステータス(408/429/5xx)のハンドリング。
    - 401 エラー検出時のトークン自動リフレッシュ（1 回）とモジュールレベルの ID トークンキャッシュ。
    - JSON デコードエラーハンドリング、ネットワーク例外処理、Retry-After ヘッダ優先処理（429）。
    - データ保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - DuckDB への冪等保存（ON CONFLICT DO UPDATE）。
      - fetched_at を UTC ISO8601 で記録。
      - PK 欠損行のスキップとログ警告。
      - 型変換ユーティリティ _to_float / _to_int（堅牢な空値・不正値処理）。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからの記事収集と前処理機能。
    - defusedxml を使った安全な XML パース、防御的実装（XML Bomb 等への配慮）。
    - URL 正規化機能（スキーム/ホストを小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 受信サイズ制限（最大 10MB）、HTTP(S) スキーム検証、SSRF 緩和策。
    - 記事 ID を正規化 URL の SHA256 ハッシュで生成し冪等性を保証。
    - バルク INSERT 用チャンク処理とトランザクションでの DB 保存最適化。
    - デフォルト RSS ソース定義（yahoo_finance）。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value 系ファクター計算を実装（prices_daily / raw_financials を参照）。
    - mom_1m/mom_3m/mom_6m / ma200_dev（200日 MA）、ATR(20), atr_pct、avg_turnover、volume_ratio、per, roe などを算出。
    - ウィンドウ不十分時は None を返す堅牢な設計。
    - SQL ベースの集計でスキャン範囲を限定（パフォーマンス配慮）。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算(calc_forward_returns)（ホライズン指定、入力検証）
    - IC（Spearman）の計算(calc_ic)、ランク変換ユーティリティ(rank)
    - ファクター統計要約(factor_summary)
    - 外部ライブラリに依存しない純 Python 実装（DuckDB 接続を受け取り prices_daily のみ参照）。

  - src/kabusys/research/__init__.py にエクスポートを追加。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールで計算した生ファクターを読み込み、ユニバースフィルタ（最低株価・最低売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日次単位の置換（BEGIN/DELETE/INSERT/COMMIT を使用して原子性を確保）。
    - 欠損やトランザクション失敗時のロールバック処理とログ出力。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）算出ユーティリティを実装（シグモイド変換等）。
    - ユーザー指定 weights の検証・フォールバック・リスケール処理（負値・非数を無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負であることを検出、サンプル閾値あり）。
    - BUY: threshold 超過で生成（Bear 時は抑制）。
    - SELL: ストップロス（終値/avg_price - 1 < -8%）と final_score 低下の判定を実装。価格欠損時の売却判定スキップと警告ログ。
    - signals テーブルへの日次単位置換（トランザクションで原子性を保証）。

- strategy パッケージエクスポート
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### Changed
- なし（初期リリースのため変更履歴はありません）。

### Fixed
- なし（初回リリース）。

### Security
- news_collector: defusedxml を利用した安全な XML パース、受信サイズ制限、URL スキーム検証など SSRF / XML Bomb / メモリ DoS を考慮した実装を導入。

### Notes / Known limitations
- signal_generator のトレーリングストップや時間決済（保有 60 営業日超過）等、いくつかのエグジット条件は docstring に「未実装」として記載されています（positions テーブルに peak_price / entry_date 等の追加が必要）。
- duckdb に依存する SQL スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）は別途用意する必要があります。
- jquants_client は環境変数 JQUANTS_REFRESH_TOKEN を必要とします（Settings 経由で取得）。
- 実行環境によってはネットワーク/API の挙動に応じた追加のエラーハンドリングや監視が必要です。

---

参考: 主要ファイル一覧
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/strategy/feature_engineering.py
- src/kabusys/strategy/signal_generator.py

（今後のリリースでは各機能の改善・テスト追加・未実装エグジットの実装などを予定しています。）