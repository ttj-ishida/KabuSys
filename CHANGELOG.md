CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  
ソース管理された変更履歴は安定した API / 機能の把握に役立ちます。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - 日本株自動売買システムのコアモジュール群を実装。
- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - .env パーサを実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内部のバックスラッシュエスケープ対応
    - クォートなしでのインラインコメント（#）の取り扱い制御
  - Settings クラスを実装して環境変数を型付け/検証付きで公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
  - 設定値の検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）の妥当性チェック。
  - データベース既定パス（DUCKDB_PATH / SQLITE_PATH）のサポート。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント評価 (news_nlp.score_news)
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) に対してバッチ評価を実行。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数制限を導入（トークン肥大化対策）。
    - JSON Mode による厳密な JSON レスポンス期待・検証ロジックを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライの実装。
    - レスポンス検証とスコアクリッピング（±1.0）、ai_scores テーブルへ冪等的に保存（DELETE → INSERT）。
    - calc_news_window による JST/UTC のニュース収集ウィンドウ計算（ルックアヘッドバイアスを避ける設計）。
    - テスト用の差し替えポイントを用意（内部の _call_openai_api を patch 可能）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - マクロニュース抽出（マクロキーワードによるフィルタ）、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 とするフォールバックを採用。
    - OpenAI API のエラー分類（429/接続/タイムアウト/5xx など）に応じたリトライ戦略。
    - テスト容易性のため API キーは引数で上書き可能、内部呼び出しはモジュール間でのプライベート関数共有を回避。

- Data モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルベースの営業日判定ロジックを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にカレンダーが存在しない場合は曜日ベース（土日非営業）でフォールバック。
    - next/prev/get_trading_days は最大探索範囲を設けて無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新（バックフィル・健全性チェック付）。
  - ETL パイプライン (pipeline.ETLResult)
    - ETL 実行の集計結果を表すデータクラス ETLResult を公開（取得数/保存数/品質チェック結果/エラー等を含む）。
    - デフォルトの差分更新 / バックフィル／品質チェック設計に対応するための土台を提供。
  - etl モジュールの公開インターフェースを追加（ETLResult の再エクスポート）。

- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などを計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比等を計算。
    - calc_value: raw_financials から EPS/ROE を参照して PER/ROE を計算（target_date 以前の最新財務データを使用）。
    - DuckDB ベースの SQL/ウィンドウ関数を活用した実装。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21）での将来リターン計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード数 3 未満で None を返す）。
    - rank: 同順位は平均ランクとするランク付け関数（丸め処理で ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

- パッケージエクスポート整理
  - __all__ による公開 API の明示（各サブパッケージで必要なシンボルを公開）。

Changed
- 設計原則の明示
  - AI 関連モジュールおよび ETL/Research モジュールは datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。
  - DuckDB をデータ処理の主要ストレージ/クエリエンジンとして想定し、直接 SQL を使う実装に統一。

Fixed
- レジリエンス改善
  - OpenAI 呼び出し箇所でのエラー分類とリトライ処理（429/接続断/タイムアウト/5xx の扱いを明確化）。
  - JSON レスポンスのパース失敗時に前後の余計なテキストから {} を抽出して復元するフォールバックを実装（news_nlp）。
  - DuckDB executemany の空リスト問題への対応（空の場合はスキップしてエラー回避）。

Security
- セキュリティ関連の変更はありません（秘匿情報は環境変数経由で扱う設計）。OpenAI API キー等は引数で注入または環境変数 OPENAI_API_KEY を利用。

Notes / Implementation details
- OpenAI クライアントは OpenAI(api_key=...) を直接生成して使用。テスト時は内部の _call_openai_api を unittest.mock.patch して差し替え可能。
- DB への書き込みは各所で BEGIN / DELETE / INSERT / COMMIT を行い冪等化を図る。失敗時は ROLLBACK を試行し、ROLLBACK の失敗はログ出力。
- いくつかの関数名・定数（例: _BATCH_SIZE, _MA_WINDOW, _MAX_RETRIES 等）はモジュール上部に定義されており、チューニング可能。
- ドキュメンテーションは各モジュールに docstring と設計方針を含む形で整備。

References
- ソース内の docstring と関数名から機能・設計方針を推測して記載しています。実際の運用や API の詳細は該当ソースを参照してください。