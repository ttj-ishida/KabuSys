# CHANGELOG

すべての変更は「Keep a Changelog」準拠の形式で記載しています。  
この CHANGELOG は提示されたソースコードの内容から推測して作成しています。

全体方針:
- バージョンはパッケージ内の __version__ = "0.1.0" を基準に初期リリースを記録しています。
- 設計上の重要な決定（ルックアヘッドバイアス回避、失敗時のフェイルセーフ、冪等書き込みなど）も注記しています。

## [Unreleased]

### Added
- ドキュメントやテストに便利なフック・設計注記を導入
  - OpenAI 呼び出しをテストで差し替え可能にする内部関数（_call_openai_api）の存在を各 ai モジュールで用意。
  - .env 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### Known issues / TODO
- ETL モジュール内の _get_max_date 関数の実装が途中（ソースに断片的な文字列 "date.fro" が残っている）。修正が必要。

---

## [0.1.0] - 2026-03-31

初回リリース — コア機能の実装とデータパイプライン / リサーチ / AI スコアリング基盤の整備。

### Added
- パッケージ基盤
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - パッケージバージョンを __version__ = "0.1.0" に設定。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env 読み込み機構:
    - プロジェクトルートを .git または pyproject.toml で自動検出して .env / .env.local を順次読み込み。
    - .env.local は .env を上書きする（ただし既存 OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して値を抽出。
    - インラインコメントの取り扱いを改善（クォートあり/なしでのコメント解釈を分離）。
  - 必須変数取得時に未設定なら ValueError を投げる _require ユーティリティ。
  - 各種設定プロパティを提供（J-Quants, kabu ステーション, Slack, DBパス, 監視閾値, ログレベル, 環境判定等）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ処理（最大 20 銘柄／リクエスト）とトークン肥大化対策（記事数・文字数上限）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライを実装。
    - レスポンスの厳密バリデーション（JSON 抽出・results 構造チェック・スコア数値化・不正値除外）を実装。
    - スコアは ±1.0 にクリップ。書き込みは部分失敗に強い「削除→挿入」の冪等処理。
    - datetime.today()/date.today() を直接参照せず、外部から target_date を与える設計でルックアヘッドバイアスを回避。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を判定して保存。
    - マクロニュースは特定キーワードでフィルタして最大 N 記事を LLM に送信。
    - OpenAI 呼び出しのリトライ / フェイルセーフ処理（API 失敗時は macro_sentiment=0.0）。
    - レジーム合成値はクリップされ、閾値でラベル付け。
    - DB への書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に実行。
    - news_nlp モジュールと実装を分離しモジュール結合を避ける設計。

- Data / ETL（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーメッセージ等を保持）。
    - 差分取得、バックフィル、品質チェックの設計方針を実装（J-Quants クライアント参照）。
    - DuckDB を使ったテーブル存在チェック等のユーティリティを提供。
  - ETL インターフェース公開（kabusys.data.etl: ETLResult の再エクスポート）。
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先だが未登録日は曜日ベースでフォールバックする一貫した振る舞い。
    - カレンダー夜間更新ジョブ calendar_update_job を実装（J-Quants から差分取得して保存、バックフィル、健全性チェックあり）。
    - 最大探索日数・バックフィル日数・先読み期間等を定数で管理。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20日 ATR）、Value（PER/ROE）などの実装。
    - DuckDB 内の prices_daily / raw_financials テーブルのみ参照する安全設計。
    - 結果は (date, code) をキーにした辞書リストで返却。
  - 特徴量解析ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズン対応、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）：ランク相関（Spearman）を実装。
    - ランク化ユーティリティ（rank）および統計サマリー（factor_summary）。
    - pandas 等に依存せず標準ライブラリのみでの実装。

- その他
  - デフォルトで使用する DB ファイルパス（duckdb/sqlite）や監視閾値（CPU/MEM/DISK）、PID ファイルパスのデフォルト値を Settings に定義。
  - 環境 (development/paper_trading/live) とログレベルの検証を Settings で実施。

### Changed
- N/A（初回リリースのため変更履歴はなし）

### Fixed
- .env パーサーの堅牢化（コメント・クォート・エスケープ処理の改善）。

### Security
- OpenAI API キーや Slack トークン等の機密情報は環境変数から取得する方式を採用。
- 自動 .env 読み込み時も既存 OS 環境変数を保護する仕組みを導入。

### Design / Reliability highlights
- ルックアヘッドバイアス対策：date/time の取得は外部から受ける（target_date 指定）ことで再現性のあるバッチ処理を実現。
- フェイルセーフ：外部 API（OpenAI, J-Quants）失敗時は例外を過度に投げず、デフォルト値やスキップで継続する設計。
- 冪等性：DB 書き込みは基本的に削除→挿入や ON CONFLICT 相当の手法で冪等に行う。
- テスト容易性：OpenAI 呼び出しや環境読み込みの差し替えポイントを明示。

### Known issues / Limitations
- パッケージ内に ETL モジュールの実装途中と思われる箇所（_get_max_date の途中記述）が存在。CI/テストでエラーとなる可能性あり。早急な修正推奨。
- 一部外部クライアント（jquants_client）の実体は参照されているが、このCHANGELOG作成時点での実装有無はソース全体からは確認できない（外部依存）。
- OpenAI 依存部分は API 仕様やモデル名（gpt-4o-mini）に依存しているため、将来的な SDK/API 変更に対する追従が必要。

---

この CHANGELOG はソースコードの注釈・設計コメントおよび実装内容から推測して作成しています。必要であれば、各項目についてソース内該当箇所の参照（ファイル名と関数名）を付記できます。どの程度詳細にリンクさせるか指定してください。