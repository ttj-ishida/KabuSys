CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
リリース日付はパッケージ内の __version__ に対応しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-28
--------------------

Added
- 基本パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py により __version__ = "0.1.0" を設定。
    - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に定義。
- 環境設定/ロード機能 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装。プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイル読み込み時の上書き挙動:
    - 優先順: OS 環境変数 > .env.local > .env
    - override / protected の概念に基づき OS 環境変数を保護。
  - 高機能な .env パーサ:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱いなどを実装。
  - Settings クラス:
    - 必須環境変数取得メソッド（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - デフォルト値と検証（KABUSYS_ENV の有効値チェック、LOG_LEVEL の検証）。
    - DB パス既定値 (DUCKDB_PATH: data/kabusys.duckdb, SQLITE_PATH: data/monitoring.db) を提供。
    - ヘルパープロパティ: is_live / is_paper / is_dev。
- AI モジュール (src/kabusys/ai)
  - ニュースNLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとに OpenAI (gpt-4o-mini) によりセンチメントを評価し、ai_scores テーブルへ書き込む機能 score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の定義）を calc_news_window で提供。
    - 1銘柄あたり最大記事数・最大文字数制限（トークン肥大化対策: _MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - チャンク処理（最大 20 銘柄／回）と JSON mode を用いた API 呼び出し。
    - リトライ戦略: レート制限・ネットワーク断・タイムアウト・5xx サーバーエラーに対して指数バックオフでリトライ。
    - レスポンスの厳密なバリデーションと数値クリップ（±1.0）。不正レスポンスや API 失敗時は該当チャンクをスキップし、他の銘柄データは保護。
    - 書き込みは部分失敗に備え、該当コードのみ DELETE → INSERT の置換を行い既存スコアを守る。
    - 外部依存: OpenAI SDK（OpenAI クライアントを引数に渡すか環境変数 OPENAI_API_KEY を使用）。
    - モジュール公開: score_news（src/kabusys/ai/__init__.py でエクスポート）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを重み合成して日次の市場レジーム（'bull' / 'neutral' / 'bear'）を判定する score_regime を実装。
    - 合成比率: MA 成分 70%、マクロセンチメント 30%。スコアは -1.0～1.0 にクリップ。閾値によりレーベルを決定。
    - LLM 呼び出しは gpt-4o-mini の JSON mode を使用。API 失敗時は macro_sentiment=0.0 のフェイルセーフを適用。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - ルックアヘッドバイアス対策として target_date 未満のデータのみを参照し、datetime.today() を直接参照しない設計。
- データプラットフォーム / カレンダー管理 (src/kabusys/data/calendar_management.py)
  - market_calendar を用いた営業日判定・探索ユーティリティを実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が未取得/まばらな場合は曜日ベースのフォールバック（週末除外）を採用し、一貫性を維持。
    - 夜間バッチ更新: calendar_update_job により J-Quants から差分取得 → 保存処理（jq.fetch_market_calendar / jq.save_market_calendar を呼出）。
    - 安全機構: 最大探索日数制限、バックフィル期間、健全性チェック（将来日付の異常検出）を実装。
- ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを実装（target_date, fetched/saved counts, quality_issues, errors）。
  - ETLResult に to_dict, has_errors, has_quality_errors といったユーティリティを提供。
  - ETL パイプライン設計に基づくユーティリティ関数（テーブル存在確認、最大日付取得 等）を実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート（src/kabusys/data/etl.py）。
- リサーチ/ファクター計算 (src/kabusys/research)
  - factor_research.py:
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を計算する関数群:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB SQL を用いた計算（prices_daily / raw_financials のみ参照）。結果は (date, code) キーの dict リストで返却。
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ρ）計算 calc_ic、ランク化 util rank、統計サマリー factor_summary を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - パッケージ公開: research.__init__ で主要関数群と zscore_normalize をエクスポート。
- データユーティリティ: calendar / pipeline 内で DuckDB と連携するための互換性考慮や NULL 処理の厳密化を実装（例: true_range の NULL 伝播制御、DuckDB executemany の空リスト回避等）。
- ロギング: 各モジュールで詳細な info/debug/warning ログメッセージを追加し、失敗時に挙動が追跡しやすいように設計。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用する設計。キー未設定時は ValueError を投げることで誤運用を防止。

Notes / Implementation details (重要な設計判断)
- ルックアヘッドバイアス回避:
  - AI モジュール、リサーチモジュールともに datetime.today()/date.today() をプロンプトや計算内部で参照せず、明示的に渡された target_date の過去データのみ参照する設計。
- フェイルセーフ:
  - LLM 呼び出しや外部 API エラー時は例外を直接上位に伝播させず、部分的にスコアを 0 にする、チャンクをスキップする等、実稼働で安全に稼働するようにしている。
- DB 書き込みは可能な限り冪等性を保証（DELETE→INSERT、ON CONFLICT の使用を想定）。
- テスト容易性:
  - OpenAI 呼び出し部は内部でヘルパー関数に分離しており、unittest.mock.patch による差し替えが容易。

今後の予定（例）
- strategy / execution / monitoring モジュールの詳細実装と公開 API の整備
- ドキュメント（使用例、ETL 実行手順、DB スキーマ、運用ガイド）の充実
- 単体テスト・統合テストの追加と CI 化

---

注: 上記はソースコードから推測した初期リリースの変更点をまとめたものです。実際のリリースノートやリリース日・バージョンはパッケージ配布時の情報に合わせて調整してください。