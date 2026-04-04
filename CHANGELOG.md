Changelog
=========

すべての注目すべき変更履歴を記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

注: このリポジトリはバージョン 0.1.0 として初回リリースされています。  
リリース内容はコードベース（src/kabusys 以下）から推測して記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ基盤
  - 初期パッケージ実装を追加（kabusys パッケージ、__version__ = 0.1.0）。
  - __all__ で主要サブパッケージを公開：data, strategy, execution, monitoring（存在しないモジュールは将来追加予定）。
- 環境設定（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの取り扱いなどに対応。
  - Settings クラスを提供（環境変数から各種設定を取得）
    - J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / 実行環境（development/paper_trading/live） / ログレベル等。
    - env と log_level の値バリデーション実装。
- データ関連（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダー操作用ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未登録のときは曜日ベースのフォールバック（週末を非営業日）を採用。
    - カレンダーバックフィル・健全性チェック・最大探索日数制限を実装。
    - 夜間バッチ（calendar_update_job）で J-Quants クライアントから差分取得 → 保存（冪等/上書き）する処理を実装。
  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを公開。ETL 実行結果（取得件数、保存件数、品質検査結果、エラー等）を集約。
    - ETL の設計方針を反映（差分更新・バックフィル・品質チェックの取り扱い等）。
    - DuckDB に対する存在チェック・最大日付取得などのユーティリティを実装。
  - ETL/パイプラインは jquants_client と quality モジュールと連携する設計（保存は冪等）。
- AI（kabusys.ai）
  - ニュースセンチメント（news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini / JSON Mode）へバッチ送信して ai_scores を生成する score_news を実装。
    - チャンク単位 (_BATCH_SIZE=20) の処理、1 銘柄あたりの最大記事数・文字数制限（トリム）を実装。
    - API エラー（429、ネットワーク、タイムアウト、5xx）に対する指数的バックオフとリトライ実装。
    - レスポンスの厳格なバリデーション（JSON 抽出・results 配列・コード照合・数値チェック）を実装。スコアは ±1 にクリップ。
    - DuckDB の executemany に対する空パラメータ回避（空リスト時の挙動に対処）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロ記事はキーワードベースで抽出（キーワードリストを定義）し、最大記事数で切り詰めて LLM に投げる。
    - LLM 呼び出しは JSON 出力を期待し、API 失敗時は macro_sentiment=0.0 でフォールバック（例外を投げず処理継続）。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）と例外時の ROLLBACK 保護を実装。
    - OpenAI クライアント生成は引数 api_key または環境変数 OPENAI_API_KEY を使用。
- 研究用機能（kabusys.research）
  - ファクター計算（factor_research）を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - calc_value: PER、ROE（raw_financials の最新報告から取得）。
    - いずれも DuckDB の prices_daily / raw_financials を参照し、副作用なしで結果リストを返す。
    - 日付扱いは lookahead バイアス回避のため date.today() を参照しない設計。
  - 特徴量探索（feature_exploration）を実装:
    - calc_forward_returns: 任意ホライズンの将来リターン（デフォルト [1,5,21]）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）。
    - rank, factor_summary: ランク計算（同順位は平均ランク）と基本統計量サマリー。
    - ランク計算は浮動小数誤差対策として round(..., 12) を使用。
- ロギングと診断
  - 各モジュールで詳細な logger.debug / logger.info / logger.warning を追加し、運用時の可視性を確保。
- テスト親和性
  - _call_openai_api などの低レベル呼び出しはテストで差し替え可能（unittest.mock.patch を想定）。

Changed
- 初回リリースにつき該当なし（新規導入）。

Fixed
- 初回リリースにつき該当なし（新規導入）。

Security
- 初回リリースにつき該当なし。

Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス防止:
  - AI スコアリング / レジーム判定 / ファクター計算は外部に依存する日付参照（datetime.today()/date.today()）を内部で直接参照しない設計。全て target_date を明示渡しで処理する。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時は処理を全面停止させず、可能な範囲でフォールバックして進める（例: マクロセンチメント = 0.0、欠損銘柄はスキップ）。
- DuckDB 互換性・制約回避:
  - executemany に空リストを渡さないガード、list 型バインド不安定性への対処（個別 DELETE の利用）など、DuckDB のバージョン差分を考慮。
- トランザクション安全性:
  - DB 書き込みは明示的にトランザクションで囲み、例外時は ROLLBACK を試みる（ROLLBACK 失敗時は警告ログ）。

今後の予定（推測）
- strategy / execution / monitoring サブパッケージの具体実装追加。
- jquants_client, quality 等の依存モジュールの実装・連携強化。
- ドキュメント（Usage / API / Deployment）と追加のユニット／統合テスト整備。

----
この CHANGELOG はコードの現状から推測して作成しています。実際のコミット履歴や変更履歴があればそれに合わせて更新してください。