CHANGELOG
=========

すべての重要な変更を記録します。本ドキュメントは "Keep a Changelog" の形式に準拠します。

フォーマットの説明:
- 各リリースは日付を付与します（YYYY-MM-DD）。
- セクションは主に Added / Changed / Fixed / Removed / Security / Notes を使用します。

[Unreleased]
------------

- なし（初回リリースのみ）。


[0.1.0] - 2026-03-21
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: __version__ = "0.1.0"。
- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサを強化:
    - コメント・空行スキップ、"export KEY=val" 形式サポート。
    - シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、クォートなし時のコメント判定。
  - 環境変数の保護機構（override/protected）を実装し、OS 環境変数を上書きしない挙動を提供。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level）等のプロパティを提供。値検証（有効な env 値や log level）を行う。
- データ取得・保存 (kabusys.data)
  - J-Quants クライアント (jquants_client):
    - API 呼び出しユーティリティを実装（_request）。
    - 固定間隔のレートリミッタ実装（120 req/min を遵守）。
    - 再試行（指数バックオフ）ロジックを実装（最大 3 回、408/429/5xx 対象）。
    - 401 受信時のリフレッシュトークンによる自動トークン再取得（一回のみリトライ）。
    - ページネーション対応（pagination_key の扱い）。
    - DuckDB への冪等保存関数を実装:
      - save_daily_quotes: raw_prices への INSERT ... ON CONFLICT DO UPDATE。
      - save_financial_statements: raw_financials への冪等保存。
      - save_market_calendar: market_calendar への保存。
    - データ型変換ユーティリティ (_to_float, _to_int) を追加し、不正値を安全に扱う。
    - fetched_at を UTC ISO8601 で記録し、データ収集時刻（Look-ahead バイアス検証用）を保存。
  - news_collector:
    - RSS フィードからの記事収集ロジック（XML パース、テキスト前処理、正規化）を追加。
    - URL 正規化（tracking パラメータ削除、ソート、フラグメント除去）ユーティリティを実装。
    - メモリ DoS 対策として受信最大バイト数を制限（MAX_RESPONSE_BYTES = 10MB）。
    - 冪等性のため記事 ID を URL 正規化後のハッシュで生成する設計（説明）。
    - defusedxml を利用し XML 関連の攻撃を軽減する設計。
- リサーチ・ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を元に各種ファクター（mom_1m/3m/6m、ma200_dev、atr_20/atr_pct、avg_turnover、volume_ratio、per, roe 等）を計算。
    - 計算に必要なスキャン期間や窓幅（例: MA200, ATR20 等）を定義し、データ不足時の None 返却を適切に扱う。
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターン（1/5/21 営業日等）を計算する機能。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ。データ不足時は None を返す。
    - rank / factor_summary: ランク付け・統計サマリーを提供。
  - research パッケージの __all__ を整備。
- 戦略 (kabusys.strategy)
  - feature_engineering.build_features:
    - research 側の生ファクターをマージ・ユニバースフィルタ（最低株価/最低平均売買代金）を適用。
    - 正規化（z-score）・±3 クリップ処理を行い features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）。
    - DuckDB に対するトランザクション管理（BEGIN/COMMIT/ROLLBACK）を実装。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを算出。
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）、重み付け合算（デフォルト重みを提供）による final_score 計算。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）による BUY 抑制。
    - BUY/SELL シグナル生成（BUY は threshold 以上、SELL はストップロスやスコア低下等）、signals テーブルへ日付単位で置換（トランザクション）。
    - 重みの検証と正規化（未知キーや不正値は無視、合計が 1 でない場合は再スケール）。
    - positions と prices の参照によりエグジット判定（ストップロスを含む）。
  - strategy パッケージの __all__ を整備。
- ロギング:
  - 各モジュールで詳細ログ（info/debug/warning）を多用し処理追跡を容易に。

Changed
- なし（初回公開）。

Fixed
- なし（初回公開）。

Removed
- なし（初回公開）。

Security
- RSS パースに defusedxml を使用して XML ベースの攻撃を緩和。
- news_collector における受信サイズ制限や URL 正規化等により SSRF / DoS リスクを低減する設計を導入。
- J-Quants クライアントでのトークン自動更新とレート制御により、認証失敗や API 制限に対する耐性を向上。

Notes / Known limitations
- signal_generator の SELL 判定ではトレーリングストップ（peak_price に基づく）や時間決済（保有60営業日超）など一部条件は未実装（positions テーブルに peak_price / entry_date 等の追加が必要）。
- feature_engineering では avg_turnover をユニバースフィルタに使用するが、features テーブルには保存しない設計。
- DuckDB の対象テーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）が事前に適切に作成されていることが前提。
- news_collector の詳細な SSRF/ホストIP検査（ipaddress/socket を用いる実装）は設計思想に含まれるが、実装の細部は将来的な拡張対象。
- research/feature_exploration は外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装しているため、大規模データ処理での最適化は今後の課題。

開発者向けメモ
- 環境変数の自動ロードはプロジェクトルート探索に依存するため、パッケージ配布後の動作を意識する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的にロード制御を行うこと。
- J-Quants API 呼び出しは rate limiter と retry を備えるが、運用時はログとモニタリングを必ず有効化してください（429 や 5xx での待機挙動確認のため）。
- DuckDB トランザクション処理で例外発生時に ROLLBACK を試みるが、ROLLBACK 自体が失敗する可能性をログで拾う設計（ローカルでのテストを推奨）。

作者
- kabusys 開発チーム

README やドキュメントに追記する提案
- セットアップ手順（.env.example の説明、必要な環境変数一覧）
- 必要な DuckDB スキーマ定義（テーブル一覧とカラム型）
- 運用時の注意点（API レート制限、ログレベル、KABUSYS_ENV の使い方）
- News collector の外部アクセス制限ポリシー（プロキシ/タイムアウト 等）