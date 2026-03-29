# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠し、リリースごとに主要な追加・変更・修正点をまとめています。

現在のバージョンは src/kabusys/__init__.py に記載の通り 0.1.0 です。

## [Unreleased]
- 将来の変更・修正をここに記載します。

## [0.1.0] - 2026-03-29
初回公開リリース。本リポジトリのコア機能群を実装しました。主要な追加点・設計方針・注意点は以下のとおりです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージを追加。__version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に公開（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env / .env.local を読み込む（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理をサポート。
    - .env.local は .env の値を上書き（ただし OS 環境変数は保護）。
  - Settings クラスを提供し、アプリケーションで使う主要設定をプロパティとして公開（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル 等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（不正値は ValueError）。
    - デフォルトの DB パス（DuckDB / SQLite）や API ベース URL のデフォルト値を設定。

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチで送信して銘柄別スコアを生成。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として提供。
    - バッチサイズ、記事数/文字数トリム、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証（JSON 抽出・results の検証・スコアの型検証）を実装。
    - DuckDB への書き込みは部分的に冪等（成功した銘柄のみ DELETE → INSERT）で行い、部分失敗時に既存データを保護。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に設計（_call_openai_api を patch 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF（1321）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の算出（target_date 未満のデータのみ利用しルックアヘッド回避）と、マクロ記事抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー・パースエラー時はフェイルセーフとして macro_sentiment = 0.0 を採用し継続。
    - OpenAI 呼び出しのリトライ・バックオフ実装および 5xx の扱いに対応。

- データ基盤ユーティリティ (src/kabusys/data)
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を利用した営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した振る舞いを採用。
    - calendar_update_job による J-Quants からの差分フェッチ・保存ロジック（バックフィル・健全性チェック含む）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分更新・保存・品質チェックの想定フローを実装。ETLResult データクラスを定義し、実行結果・品質問題・エラーを集約して to_dict を提供。
    - jquants_client を使ったデータ取得と保存を想定。
    - DuckDB の互換性問題（executemany に空リストを渡さない等）を考慮した実装。

- 研究モジュール (src/kabusys/research)
  - factor_research.py
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、流動性（20日平均売買代金・出来高比率）、Value（PER/ROE）などのファクター計算を実装。DuckDB 上の SQL を中心に計算。
    - 不足データの取り扱い（十分な期間がなければ None を返す）・ログ出力を実装。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、rank ユーティリティ、統計サマリー（count/mean/std/min/max/median）を実装。
  - research パッケージ __all__ を整備して主要機能を公開。

### 変更 (Changed)
- 設計方針の明文化
  - 多箇所で「ルックアヘッドバイアス回避」のために datetime.today()/date.today() を直接参照しない設計を採用（関数は target_date を引数で受け取る）。
  - OpenAI など外部 API 呼び出しに対しては「失敗しても処理を継続する（フェイルセーフ）」方針を採用。致命的な場合のみ例外を伝播。

### 修正 / 安全対策 (Fixed / Security)
- 環境変数読み込みで OS 環境変数を意図せず上書きしないよう保護機構を実装（protected set）。
- DuckDB の実装差異に対応するため、executemany に空リストを渡さないガードを追加。
- JSON Mode のレスポンスに対し、前後に余計なテキストが混じるケースへ復元（最外の {} を抽出）するロバストなパーシングを導入。
- 外部キーや DB 書き込みにおける冪等性を確保（DELETE→INSERT のパターンや BEGIN/COMMIT/ROLLBACK の扱い）。

### ドキュメント / 開発支援 (Docs / Dev)
- 各モジュール冒頭に処理フロー・設計方針・注意点を詳細にコメントとして記載。テストを容易にする設計（API キー注入、_call_openai_api の差し替えポイントなど）を盛り込む。

### 既知の制約・注意点 (Known issues / Notes)
- OpenAI SDK のバージョンや API の挙動変化（response_format の挙動や例外クラスの変更など）によっては追加対応が必要になる可能性があります（コード内で status_code の存在を getattr で安全に扱う等の互換性対策は入れています）。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や特異なプロジェクト構成では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で設定する運用を推奨します。
- ai モジュールは外部 API（OpenAI）に依存するため、レート制限やコスト・プライバシーに配慮した運用が必要です。
- 現時点で一部のファクター（PBR・配当利回り等）は未実装（calc_value の注記参照）。

---

（注）この CHANGELOG は、与えられたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。必要であれば、コミット単位の変更点や追加のリリース日付・作者情報を反映した修正版を作成します。