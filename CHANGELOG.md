CHANGELOG
=========

すべての注目すべき変更を時系列で記載します。本ファイルは「Keep a Changelog」準拠で書かれています。

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリース。
- 基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- コア初期化
  - src/kabusys/__init__.py によるパッケージ公開（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない探索を実装。
  - .env パーサー:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、コメントの扱い（クォートなしでは '#' の直前が空白/タブのときのみコメント扱い）などを実装。
  - Settings クラスでアプリケーション設定をプロパティとして公開:
    - J-Quants / kabuステーション / Slack / データベースパス（duckdb/sqlite）/ログレベル/環境（development/paper_trading/live）など。
    - 必須設定未定義時は明示的に ValueError を送出するバリデーションを実装。
    - env 値の妥当性チェック（許容値セット）を実装。

- AI モジュール（src/kabusys/ai）
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を取得。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window として実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数/文字数上限（トリム）を実装。
    - API リトライ戦略（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、レスポンス検証（JSON 抽出、results 構造・型チェック、未知コードの無視、スコアを ±1 にクリップ）を実装。
    - DuckDB へは冪等的に（DELETE → INSERT）スコアを書き込むロジックを実装。部分失敗時に既存スコアを保護する手順を採用。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッドバイアス回避）。
    - マクロニュース抽出（マクロキーワード群）→ OpenAI 呼び出し（gpt-4o-mini）→ スコア合成。
    - API エラーやパースエラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB 書き込み失敗時は ROLLBACK を試行して上位へ例外を伝播。

- データプラットフォーム（src/kabusys/data）
  - calendar_management (src/kabusys/data/calendar_management.py)
    - JPX マーケットカレンダー（祝日・半日取引・SQ 日）の管理と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得のときは曜日ベースのフォールバック（週末を休日扱い）を採用し、一貫した挙動を保証。
    - calendar_update_job を実装し、J-Quants API 経由で差分取得・冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）を行う。バックフィル・健全性チェックあり。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL 処理のインターフェースとユーティリティを実装。
    - ETLResult dataclass（取得件数・保存件数・品質チェック結果・エラー情報等）を提供。to_dict により品質問題をシリアライズ可能。
    - 差分取得のための内部ユーティリティ（テーブル存在確認 / 最大日付取得）を実装。
    - デフォルトのバックフィル日数やカレンダ利用方針を定義。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
  - jquants_client（外部統合ポイント）を参照する設計になっており、API 経由でデータ取得・保存が可能。

- 研究 / ファクター（src/kabusys/research）
  - factor_research (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER・ROE）を計算する関数を実装。
    - DuckDB 内の prices_daily / raw_financials のみを参照する設計（外部 API 呼び出し無し）。
    - データ不足時の None 戻し、結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクタ要約（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - スピアマンランク相関の計算、欠損/定数系列の扱い、rank の同順位処理（平均ランク）などを実装。
  - research/__init__.py により主要関数群を公開（zscore_normalize は data.stats から再利用）。

Other notable implementation details / design decisions
- ルックアヘッドバイアス対策:
  - news/レジーム/ファクター計算で datetime.today() / date.today() を直接参照しない設計。全て target_date ベースで計算。
- フェイルセーフ / エラーハンドリング:
  - OpenAI API 呼び出しはリトライ・バックオフ・パース障害時のフォールバックを実装し、致命的停止を避ける方針。
  - DB 書き込みは冪等化およびトランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を保つ。
- テスト支援:
  - AI モジュールの OpenAI 呼び出しを差し替え可能にしてユニットテストを容易にする設計（patch 可能な内部関数）。
- DuckDB 互換性考慮:
  - executemany に空リストを渡さない等、DuckDB の既知制約への対応を組み込んでいる。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- jquants_client の実装（API クライアント）は別モジュールとして参照しており、本リリースでは外部 API 統合ポイントを定義。実環境での動作には該当クライアント実装および正しい API キー/環境変数が必要。
- OpenAI モデルは gpt-4o-mini を想定している。API 仕様変更時は呼び出しの互換性を確認する必要あり。
- 現段階で Strategy / execution / monitoring パッケージ本体は公開名として存在するが、個別機能の追加・拡張は今後のリリース予定。

--- 

今後のリリースでは、テストカバレッジの拡充、CI 統合、運用向け監視・アラート機能、戦略実行ロジックの追加を予定しています。もし特に注目してほしい箇所や追記してほしい変更点があれば教えてください。