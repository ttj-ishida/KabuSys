# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、提供されたコードベースの内容から実装された機能・設計意図・エラーハンドリング等を推測して作成した変更履歴です。

## [Unreleased]
（今後の変更・改善予定をここに記載）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買・データ基盤・リサーチ支援・AI スコアリングの基盤機能を実装。

### Added
- パッケージ初期公開
  - kabusys パッケージの公開インターフェースを追加（__version__ = 0.1.0, __all__ に主要サブパッケージを列挙）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - OS 環境変数を保護するための上書き制御（protected set）を実装。
  - 必須環境変数取得用の _require() と Settings クラスを追加。J-Quants / kabu / Slack / DB（DuckDB/SQLite）設定、環境（development/paper_trading/live）・ログレベル検証などを提供。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄単位でニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードを使ってセンチメントを算出、ai_scores テーブルへ保存する処理を実装。
  - バッチ処理（最大20銘柄/チャンク）、1銘柄当たりの記事数・文字数トリム、結果バリデーション、スコアの ±1.0 クリップを実装。
  - API エラー（429、ネットワーク、タイムアウト、5xx）に対して指数バックオフでリトライし、失敗時はスキップして処理継続するフェイルセーフを備える。
  - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。

- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みするスクリプトを実装。
  - MA 計算は target_date 未満のデータのみを利用してルックアヘッドバイアスを防止。
  - OpenAI API 呼び出しに対するリトライとフェイルセーフ（API 失敗時 macro_sentiment = 0.0）を実装。
  - レジーム算出の閾値・スケーリング・重みなどを定数化し可読性を確保。

- データ基盤（kabusys.data）
  - カレンダー管理（calendar_management）:
    - market_calendar を用いた営業日判定（is_trading_day）、翌/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日リスト取得（get_trading_days）、SQ日判定（is_sq_day）を実装。
    - DB に登録がない日については曜日ベース（土日を休業日）でフォールバックする一貫したロジックを採用。
    - calendar_update_job により J-Quants からの差分取得、バックフィル、健全性チェック（将来日異常検知）を行い、冪等的に保存する処理を実装。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを導入し、ETL 実行の取得数/保存数・品質検査結果・エラーを構造化して返却。
    - テーブル存在チェック・最大日付取得等の内部ユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、出来高系）、Value（PER, ROE）を DuckDB 上の SQL + Python で実装。
    - 欠損やデータ不足時の扱い（None を返す）を明確化。
  - 特徴量探索（feature_exploration）:
    - 将来リターン calc_forward_returns（複数ホライズン対応、ホライズンは営業日ベース）、IC（calc_ic, Spearman の ρ）、rank、factor_summary（count/mean/std/min/max/median） を実装。
    - pandas 等の外部ライブラリに依存せず標準ライブラリで実装。

- API・設計方針の明示
  - 主要モジュールで datetime.today() / date.today() への直接参照を避け、target_date を引数に取ることでルックアヘッドバイアスを防止する設計。
  - DuckDB をデータレイヤーに採用し、DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等性を保つ実装が随所に存在。
  - ロギングを多用して動作状況やフェイルセーフを記録。

### Changed
- （初版のため過去変更なし。実装方針・ログ出力により将来の変更が容易になる設計を採用。）

### Fixed
- （初版のため過去修正なし。ただし多くのフェイルセーフを導入して実運用時の障害耐性を高めている：OpenAI 呼び出しリトライ、応答パース失敗時のスキップ、DB トランザクションの ROLLBACK 保護等。）

### Security
- 環境変数や API キーの取り扱いに注意
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で注入。Settings により必須チェックを行う。公開リポジトリへキーをコミットしないことを推奨。

---

注意・補足
- テスト容易性のため、OpenAI 呼び出し箇所（各モジュールの _call_openai_api）は unittest.mock.patch 等で差し替え可能に設計されています。
- DuckDB のバージョン差異（list 型バインドの挙動など）を考慮して、executemany を用いた互換性の高い実装を採用しています。
- 提供されたコードは設計ドキュメントの節（StrategyModel.md、DataPlatform.md 等）を参照する想定でコメントが充実しており、実運用に向けた健全性チェックやバックフィル戦略が組み込まれています。