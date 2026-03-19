Keep a Changelog 準拠の形式で、このコードベースの初回リリース相当の CHANGELOG を推測して作成しました。

CHANGELOG.md

""" 
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/
"""

Unreleased
- なし

[0.1.0] - 2026-03-19
Added
- パッケージ初期リリース: kabusys v0.1.0 を導入
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を追加。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動ロード機能を提供（プロジェクトルート検出: .git または pyproject.toml）。
  - ロード順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - .env 行パーサ実装:
    - export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォート外で直前がスペース/タブの場合に # をコメントとみなす）。
    - 不正行のスキップと読み込み失敗時の警告。
  - Settings クラス: J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス（DuckDB/SQLite）、環境 (development/paper_trading/live) とログレベルの検証プロパティを提供。
  - 必須環境変数未設定時に明確なエラーを投げる _require ユーティリティ。

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - 固定間隔のレートリミッタ（120 req/min）とページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行、429 で Retry-After 優先）。
    - 401 発生時にリフレッシュトークンから自動で ID トークンを再取得して 1 回リトライする仕組み。
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）。
  - DuckDB への保存ユーティリティ（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT を使った upsert 実装、PK 欠損行スキップ・警告、挿入件数のログ出力。
  - 入力パース補助関数: _to_float / _to_int（安全な変換ルールを定義）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事収集して raw_news に保存:
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - URL 正規化（トラッキングパラメータ除去、フラグメント除去、キー順ソート、小文字化）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を用いることで冪等性を確保する方針を明記。
    - defusedxml を使用して XML 関連の脅威を低減。
    - 最大受信バイト数制限（10 MB）や SSRF 対策を想定した設計。（HTTP/HTTPS スキームのみ許可等を想定）
    - DB バルク挿入のチャンク化とトランザクションでパフォーマンス/原子性を確保。
    - 実際に挿入されたレコード数を正確に把握する設計。

- リサーチ（研究）機能 (src/kabusys/research/)
  - factor_research.py:
    - モメンタム、ボラティリティ、バリュー（PER/ROE 等）の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - prices_daily / raw_financials のみを参照する設計。営業日ベースのラグ（LAG/LEAD）や移動平均、ATR 等を SQL で計算。
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、データ不足時の None ハンドリング）。
    - スピアマン IC（ランク相関）を計算する calc_ic と補助 rank 関数（同順位の平均ランク処理、丸めで ties を管理）。
    - factor_summary による各ファクターの基本統計量（count/mean/std/min/max/median）。
  - research パッケージのエクスポートを提供。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research 側の生ファクターを取り込み、ユニバースフィルタ・正規化・クリップして features テーブルへ日次単位で置換保存する build_features を実装。
  - ユニバースフィルタ条件:
    - 株価 >= 300 円、20日平均売買代金 >= 5 億円。
  - Z スコア正規化（対象カラムを指定）、±3 でクリップ、トランザクション + バルク挿入による日付単位の置換（冪等性）。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して最終スコア final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ日次置換で保存する generate_signals を実装。
  - コンポーネントスコア:
    - momentum, value, volatility, liquidity, news（デフォルト重みを定義）。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
  - 重みの受け付け方:
    - ユーザ指定の weights は検証（既知キーのみ、非数/NaN/負値を除外）、合計が 1.0 でなければ再スケール。
  - Bear レジーム判定:
    - ai_scores の regime_score 平均が負である場合に Bear と判定し、BUY シグナルを抑制。
    - サンプル数が不足（デフォルト未満）なら Bear 判定は行わない。
  - エグジット（SELL）判定（_generate_sell_signals）:
    - 実装済: ストップロス (終値/avg_price - 1 < -8%)、final_score が閾値未満。
    - 未実装メモ: トレーリングストップ、時間決済は positions に必要な情報（peak_price/entry_date）が未整備のため保留。
  - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を保証。

Security
- news_collector で defusedxml を利用して XML 攻撃を軽減。
- RSS URL 正規化でトラッキングパラメータを除去し、記事 ID をハッシュ化して冪等性を担保。
- J-Quants クライアントは認証トークンの自動リフレッシュ機構を持つが、get_id_token 呼び出し時の無限再帰を防ぐため allow_refresh フラグを使用。
- API リクエストに対するレートリミッタと受信サイズ上限（ニュース 10MB）でサービス妨害を緩和。

Notes / 実装上の重要な設計判断
- DuckDB を中心としたオンディスク分析ワークフローを想定。多くの処理は SQL ウィンドウ関数で実装され、pandas 等に依存しない。
- ルックアヘッドバイアス防止を徹底（target_date 時点までのデータのみ参照、fetched_at を UTC で記録）。
- 冪等性を重視: DB への保存は upsert/DELETE+INSERT の置換パターンで実装。
- 一部の機能は「未実装（TODO）」として明記（例: トレーリングストップ、時間決済など）。positions テーブル側の拡張が必要。

Deprecated
- なし

Removed
- なし

Fixed
- 初版リリースのため履歴なし

Contibutors
- （コード内の記述に基づく推測のため省略）

---

補足:
- 本 CHANGELOG はリポジトリ中のソースコードコメント・実装内容から推測して作成した初回リリース相当の変更履歴です。実際のコミット履歴・リリースノートとは差異がある可能性があります。必要であれば、より詳細（関数ごとの挙動例、既知の制約・未実装項目の一覧、マイグレーション手順など）を追記します。