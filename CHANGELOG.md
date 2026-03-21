CHANGELOG
=========
この変更履歴は「Keep a Changelog」の形式に従って作成されています。  
バージョニングは Semantic Versioning を想定しています。

[Unreleased]
-------------
（なし）

[0.1.0] - 2026-03-21
-------------------

最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点・設計方針は以下の通りです。

Added
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = 0.1.0、主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込みを実装（プロジェクトルートを .git / pyproject.toml より探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサーの実装: コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
  - OS 環境変数を保護する protected 機構（.env.local は override=True だが既存 OS 環境変数は上書きしない）。
  - Settings クラスを提供し、必須環境変数取得の _require、env/log_level 検証、データベースパス既定値（DUCKDB_PATH / SQLITE_PATH）などをサポート。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限: 固定間隔スロットリング（120 req/min）を実装（RateLimiter）。
    - 再試行ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx 等をリトライ対象。
    - 401 応答時はリフレッシュトークンで ID トークンを自動取得して 1 回リトライする仕組みを実装（無限再帰保護あり）。
    - ページネーション対応（pagination_key を使用）。
    - 取得時刻（fetched_at）を UTC で記録し、look-ahead bias のトレースを容易に。
  - DuckDB への保存ユーティリティを実装（冪等性を考慮して ON CONFLICT DO UPDATE を使用）。
    - save_daily_quotes: raw_prices テーブルへ保存（PK 欠損行スキップ、型変換ユーティリティ _to_float/_to_int を利用）。
    - save_financial_statements: raw_financials テーブルへ保存（PK 欠損行スキップ）。
    - save_market_calendar: market_calendar テーブルへ保存（holidayDivision -> is_trading_day / is_half_day / is_sq_day のマッピング）。
  - HTTP レスポンスの JSON デコード失敗やネットワークエラーの扱いを明示。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集モジュールを追加。
    - デフォルト RSS ソース（例: Yahoo Finance のビジネスカテゴリ）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、XML 攻撃防止のため defusedxml を利用。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）機能を実装。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）等を用いる（冪等性確保を想定）。
    - DB へのバルク挿入はチャンク化して実行（_INSERT_CHUNK_SIZE）。

- 研究用モジュール (kabusys.research)
  - ファクター計算（factor_research）
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）の計算（200 日移動平均の窓チェック等）。
    - ボラティリティ/流動性（atr_20, atr_pct, avg_turnover, volume_ratio）の計算（true_range の扱い、20 日窓チェック）。
    - バリュー（per, roe）計算（raw_financials の最新レコードを参照）。
  - 特徴量探索（feature_exploration）
    - 将来リターン calc_forward_returns（複数ホライズンを同時取得、ホライズン入力検証）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンの rho、欠損・サンプル数チェック）。
    - factor_summary（count/mean/std/min/max/median）と rank（同順位は平均ランク、丸め対策あり）実装。
  - すべて DuckDB の prices_daily / raw_financials のみ参照、外部依存を極力排除する設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールで算出した生ファクターを統合・正規化し features テーブルにUPSERTする機能を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を zscore 正規化（外れ値は ±3 でクリップ）。
    - DuckDB トランザクションを用いた日付単位の置換（DELETE + INSERT、COMMIT/ROLLBACK）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコアを算出し signals テーブルへ保存する機能を実装。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（sigmoid 変換等）。
    - デフォルト重みの導入（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）と、ユーザ指定 weights の検証・正規化・フォールバック。
    - BUY 閾値デフォルト 0.60、Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）による BUY 抑制。
    - SELL（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）
      - final_score が閾値未満
      - 価格欠損時は SELL 判定をスキップして誤クローズを防止
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - signals テーブルへトランザクション付き日付単位置換を実行。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- ニュース収集で defusedxml を利用して XML 関連攻撃を軽減。
- RSS URL 正規化や受信サイズ制限、HTTP スキーム検証などで SSRF / メモリ DoS を想定した対策を明記。

Notes / 設計方針
- ルックアヘッドバイアス防止: 特に特徴量生成・シグナル生成において、target_date 時点でシステムが実際に利用可能なデータのみを参照する設計を採用。
- 冪等性: 外部データの DB 保存はできるだけ UPSERT/ON CONFLICT を使い冪等に保つ方針。
- 外部依存最小化: research モジュールは標準ライブラリ + DuckDB のみで動作するように設計。
- ロギング: 各処理で情報／警告ログを出すよう実装しており、問題発生時のトラブルシュートを支援。

既知の未実装 / 将来機能候補
- strategy 側: トレーリングストップ（peak_price 依存）や時間決済（保有 60 営業日超）などのエグジット戦略は未実装。positions テーブルの拡張が必要。
- news_collector: 記事と銘柄コードの紐付け（news_symbols への保存）ロジックは実装想定だが、現状のファイルでは詳細未完了。
- monitoring / execution 層の具体的な発注ロジックや Slack 通知等は別モジュールでの実装を想定。

ライセンス、貢献方法、開発ルールなどは別途ドキュメントを参照してください。