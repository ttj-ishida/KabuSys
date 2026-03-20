Keep a Changelog
=================

すべての重要な変更はこのファイルで管理します。  
このプロジェクトはセマンティック バージョニングに従います（http://semver.org/）。

Unreleased
----------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- 初回リリース。日本株自動売買ライブラリ "KabuSys" を追加。
- パッケージエントリポイント:
  - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を定義。
- 環境設定管理:
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して判定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途を想定）。
    - .env パーサーは export プレフィックス、クォート（シングル/ダブル）とエスケープ、インラインコメント処理、トラッキング用の保護変数（protected）に対応。
    - Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、実行環境・ログレベルの検証プロパティ等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（有効値を限定）。
- データ取得・保存（J-Quants クライアント）:
  - src/kabusys/data/jquants_client.py
    - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter 実装。
    - リトライ（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュを実装。
    - ページネーション対応 API 呼び出し（fetch_daily_quotes, fetch_financial_statements）。
    - DuckDB への冪等保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）：ON CONFLICT による上書き、fetched_at を UTC で記録。
    - レスポンスの JSON デコード検証と詳細なエラーメッセージ。
    - 型変換ユーティリティ _to_float / _to_int を追加（不正値は None にフォールバック）。
- ニュース収集:
  - src/kabusys/data/news_collector.py
    - RSS フィードからの収集機能（デフォルトに Yahoo Finance の RSS を設定）。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - defusedxml を利用した XML 安全パース、防御的な入力サイズ制限（MAX_RESPONSE_BYTES）等の脆弱性対策。
    - 記事IDを正規化 URL の SHA-256 から生成して冪等性を保証。
    - DB へはバルク挿入をチャンク化して保存。
- リサーチ / ファクター計算:
  - src/kabusys/research/factor_research.py
    - モメンタム（1m/3m/6m、MA200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials から計算。
    - 欠損データやウィンドウ不足時の扱いを明確化（不足なら None）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（horizons デフォルト [1,5,21]、範囲検証）。
    - Spearman IC（ランク相関）計算（ties を平均ランクで処理）。
    - factor_summary / rank 等の統計ユーティリティ。
  - src/kabusys/research/__init__.py で公開 API を整理。
- 特徴量作成:
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールで計算された raw factor をマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化して ±3 でクリップ。
    - 日付単位で features テーブルへ置換（削除→挿入）の原子操作（BEGIN/COMMIT、ROLLBACK 対応）。
- シグナル生成:
  - src/kabusys/strategy/signal_generator.py
    - features + ai_scores を統合して各銘柄の final_score を計算（デフォルト重みと閾値を実装）。
    - シグモイド変換、コンポーネントスコア（momentum/value/volatility/liquidity/news）算出、欠損コンポーネントは中立 0.5 で補完。
    - Bear レジーム検知（ai_scores の regime_score 平均が負で、サンプル数閾値を満たす場合）。
    - BUY（閾値超）／SELL（ストップロスまたはスコア低下）判定を実装。
    - positions / prices を参照してエグジット判定を行い、signals テーブルに日付単位で置換して書き込み（冪等）。
    - 重みの入力について不正値のスキップ・再スケール処理を実装。
- パッケージの strategy エクスポート:
  - src/kabusys/strategy/__init__.py で build_features, generate_signals を公開。

Changed
- 初期実装のため該当なし。

Fixed
- 初期実装のため該当なし。

Security
- news_collector: defusedxml を使用し XML BOM 等の攻撃に対策。
- jquants_client: ネットワーク/HTTP エラーのリトライ制御とトークン自動更新を実装し、不正な状態での多重リクエストや再帰を防止。

Notes / Known limitations / TODO
- signal_generator の SELL 判定に関する未実装箇所:
  - トレーリングストップ（peak_price / entry_date に依存）や時間決済（60 営業日超）等は未実装。positions テーブルに peak_price / entry_date を追加すると実装可能。
- build_features / generate_signals は発注層（execution API）には依存しない設計。発注・実行層は別実装を想定。
- 一部のログや警告はデータ欠損時に処理をスキップする挙動をとる（例: 価格欠損で SELL 判定をスキップする等）。運用時はデータ整備を推奨。
- .env のパーサーは多くのケースに対応しているが、特殊なエスケープや極端なフォーマットは未検証。

Authors
- KabuSys 開発チーム（コードベースから推測して記載）

ライセンス
- 明記なし（リポジトリの LICENSE を参照してください）