# Changelog

すべての notable な変更はこのファイルで管理します。  
このプロジェクトは「Keep a Changelog」形式に従っています。  

最新リリース
=============

Unreleased
----------

（現在のコードベースは v0.1.0 として初期公開相当の状態です。次回以降の変更はここに記載してください。）

履歴
====

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定/ロード機能（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定値を読み込む自動ローダーを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パース機能:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく扱う。
    - インラインコメントの扱い（クォート有無でのルール分岐）。
  - 上書き制御:
    - .env は OS 環境変数を保護（protected）しつつ .env を読み込み、.env.local は上書き（override）可能。
  - Settings クラスを提供（settings インスタンスをエクスポート）:
    - J-Quants / kabu API / LINE / DB（duckdb/sqlite） / 実行監視用パス等のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL の値チェック（許容値のバリデーション）。
    - is_live / is_paper / is_dev のユーティリティ。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとの記事を結合し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントを算出。
    - タイムウィンドウの計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して比較）。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、1 銘柄あたり記事数上限・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列の検証、未知コード無視、数値チェック）。
    - スコアを ±1.0 にクリップ。取得成功分のみ ai_scores テーブルへ置換（部分失敗時に既存スコアを保護するためコード単位で DELETE → INSERT）。
    - DuckDB の executemany の挙動（空リスト不可） に配慮した実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュースは news_nlp の calc_news_window に基づくウィンドウからマクロキーワードでフィルタして取得。
    - OpenAI 呼び出しは独立した内部実装（モジュール結合を避ける）。
    - API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルに保存。
    - リトライ、5xx 判定、JSON パース例外処理など耐障害性を考慮。

- データ処理基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar に基づく営業日判定ユーティリティを提供: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB 登録データ優先、未登録日は曜日ベースのフォールバック（週末判定）。
    - カレンダー夜間バッチ更新（calendar_update_job）: J-Quants から差分取得して保存、バックフィルや健全性チェックを実装。
    - _MAX_SEARCH_DAYS による探索上限で無限ループを防止。

  - ETL / パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult dataclass を実装（target_date, fetched/saved counts, quality_issues, errors 等）。
    - ETLResult に to_dict(), has_errors, has_quality_errors プロパティを提供。
    - DataPlatform の設計方針に沿った差分更新、バックフィル、品質チェックのスケルトン（jquants_client と quality モジュールを想定）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ATR ベースのボラティリティ、出来高/売買代金ベースの流動性指標、財務ベースの Value 指標（PER/ROE）を計算する関数を実装。
    - DuckDB SQL を活用した実装で、外部 API・発注系とは独立。
    - データ不足時は None を返すなど堅牢に動作。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）に対応、ホライズン検証あり。
    - IC（Information Coefficient）計算（calc_ic）：Spearman（ランク相関）を実装。十分なサンプル数がない場合は None を返す。
    - ランキングユーティリティ（rank）：同順位は平均ランク、浮動小数点誤差対策の丸め処理を採用。
    - ファクター統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。

Design / Notes
- ルックアヘッドバイアス回避:
  - 各種モジュール（AI スコアリング / レジーム判定 / リサーチ関数）は datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取って処理。DB クエリも target_date 未満・未満等でルックアヘッドを回避。
- 外部依存について:
  - OpenAI SDK を使用する想定（OpenAI クライアントを生成）。ただし API 呼び出し箇所はテスト時に差し替え可能（内部の _call_openai_api を patch しやすい設計）。
  - DuckDB による SQL 実行を前提（DuckDB 型の挙動や executemany の制約を考慮）。
  - 可能な限り標準ライブラリのみでリサーチ機能を実装（pandas 等へ依存しない）。
- 耐障害性:
  - OpenAI 呼び出しはリトライ / バックオフ、5xx とそれ以外の扱いを分離、失敗時にログを出してフェイルセーフで継続する方針（例: macro_sentiment=0.0、スコア未取得はスキップ）。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK 失敗時は警告ログで通知。

Fixed
- （初回リリースのため特定のバグ修正履歴はなし。実装時に DuckDB executemany 空パラメータ回避や JSON の前後余計テキスト対策など堅牢化のための処置を組み込んでいます。）

Deprecated
- なし

Removed
- なし

Security
- API キー取扱い:
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を投げることで誤操作を防止。

今後の予定（候補）
- monitoring/execution/strategy モジュール群の実装拡張（__all__ に含まれるが、現時点で未提供の機能拡張）。
- より詳細な品質チェック機能 quality モジュールの実装強化。
- テストカバレッジ追加と CI ワークフロー整備。

--- 

注: 上記はコードベースから推測して作成した CHANGELOG です。各項目の正確な文言・日付は実際のリリースポリシーに合わせて調整してください。