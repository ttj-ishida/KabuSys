KEEP A CHANGELOG
=================

すべての変更は逆時系列で記録します。  
この CHANGELOG は Keep a Changelog の形式に準拠しています。

Unreleased
---------

（なし）

0.1.0 - 2026-03-20
-----------------

初回リリース — 日本株自動売買システムのコアライブラリを追加しました。以下はコードベースから推測してまとめた主な追加・設計方針・既知の挙動です。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）、バージョン 0.1.0。
  - モジュール公開 API（__all__）に data, strategy, execution, monitoring を指定。

- 設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 環境変数のパーサ実装（コメント、クォート、export プレフィックス、エスケープを考慮）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - OS 環境変数を保護する読み込み順（OS env > .env.local > .env）と上書き制御（protected）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等のプロパティを環境変数から取得。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーションを実装。
  - 必須環境変数未設定時は明示的なエラーを発生させる _require() を導入。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限対応（固定間隔スロットリング、120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
  - 401 受信時にリフレッシュトークンで自動的にトークンを更新して再試行（1 回のみ）。
  - ページネーション対応（pagination_key を利用）。
  - 取得日時（fetched_at）を UTC ISO8601 で記録して Look‑ahead バイアス追跡を可能に。
  - DuckDB への冪等保存（raw_prices, raw_financials, market_calendar）を実装（ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ _to_float / _to_int を導入し、入力の堅牢性を向上。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集基盤を追加（デフォルトの RSS ソースに Yahoo Finance を含む）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - セキュリティ対策: defusedxml を使った XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）による DoS 防止、SSRF 対策（HTTP/HTTPS 想定）。
  - 記事 ID は正規化 URL をハッシュ化（SHA-256 の先頭など）する方針（冪等性確保）。
  - バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）で DB 書き込み負荷を制御。

- Research モジュール（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials テーブルのみ参照する純粋な factor 計算。
    - マジックナンバー（例: 21日=1ヶ月、63日=3ヶ月、200日 MA 等）やデータスキャン範囲のバッファ設計を明示。
    - 欠損・データ不足時の扱い（カウント不足で None を返す）を一貫して実装。
  - feature_exploration.py:
    - calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（同順位を平均ランクにする実装）を提供。
    - 外部依存（pandas等）を使わず標準ライブラリのみで実装する方針。
  - research パッケージ __all__ を通じて主要関数を公開。

- Strategy モジュール（src/kabusys/strategy/*）
  - feature_engineering.build_features:
    - research モジュールが計算した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入）して冪等性を確保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、複数コンポーネント（momentum/value/volatility/liquidity/news）を計算。
    - 各コンポーネントはシグモイドや逆数変換などで [0,1] にマッピングし、重み付け合算（デフォルト重みを指定）して final_score を算出。
    - デフォルト閾値で BUY（default 0.60）を判定。Bear レジーム判定により BUY を抑制可能。
    - エグジット（SELL）条件としてストップロス（終値/avg_price -1 < -8%）およびスコア低下を実装。
    - weights の入力検証・合計再スケール機能を実装（不正な値はスキップし、合計が 1 に近づくよう正規化）。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を保証。
    - 保有ポジションに対する SELL を優先して BUY リストをフィルタリングし、ランクを再付与するポリシーを実装。

Changed
- （初回リリースのため「追加」が中心。将来のリリースで変更履歴を追加予定）

Fixed
- （初回リリース — 既知の実装はコメント内に記載の制約や TODO を含む）

Notes / Known limitations
- 戦略側の未実装事項（feature comments に記載）
  - トレーリングストップや保有期間による強制決済など、一部のエグジット条件は positions テーブルに追加情報（peak_price / entry_date 等）が必要なため未実装としてコメントあり。
- News collector の一部方針（例: 記事 ID の生成、INSERT RETURNING を用いた実際の挿入数取得）や細かい実装はコメントで示されており、将来的な改良余地あり。
- DuckDB スキーマ（テーブル定義）は CHANGELOG に含まれていません。各関数は prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等の存在を前提としています。
- 外部依存は最小化（duckdb, defusedxml など）。ただし実行にはこれらの依存ライブラリと外部サービス（J‑Quants, RSS）への接続が必要。

Security
- J-Quants クライアントで取得時の JSON デコードエラーや HTTP エラーを明示的に扱い、401 リフレッシュ時の無限再帰防止等の考慮あり。
- RSS パーサに defusedxml を使用して XML ベースの攻撃を軽減。
- ニュース取得で受信最大バイト数を設定しメモリ DoS を軽減。

開発メモ / 今後の改善候補
- トレーリングストップや時間決済ロジックの実装（positions テーブルの拡張）。
- news_collector での実際の挿入数取得（INSERT RETURNING を活用）や URL のより厳格な SSRF チェックの追加。
- 戦略評価・バックテスト用のユーティリティや API のテストカバレッジ拡充。
- 外部接続（J‑Quants / Slack / kabu API）に対する統合テストとモックを整備。

ライセンス
- リポジトリに明示的なライセンスファイルがあることが望ましい（本 CHANGELOG ではソースからはライセンス情報が読み取れません）。

脚注
- 上記は提供されたソースコードのコメント・実装から推測して作成しています。実際のリリースノート作成時はコミット履歴・CHANGELOG ポリシー・リリース担当者の確認を推奨します。