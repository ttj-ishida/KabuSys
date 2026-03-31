# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従って管理しています。

現在のバージョン: 0.1.0 (初版)

注意: 以下の変更履歴はリポジトリ内のソースコード（モジュール、ドキュメンテーション文字列、実装）から推測して作成しています。

---

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ初期リリース。
- 基本パッケージ構成を追加:
  - kabusys パッケージのエントリポイント（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に定義。
- 環境設定管理モジュールを追加（src/kabusys/config.py）:
  - .env/.env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env の厳密な行パース機構を実装（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント取り扱い等）。
  - OS 環境変数の保護（ロード時の protected キー扱い、override の挙動制御）。
  - Settings クラスを提供し、必須環境変数チェックやデフォルト値、バリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - DuckDB/SQLite のデフォルトパス（DUCKDB_PATH, SQLITE_PATH）設定を用意。
- AI モジュールを追加（src/kabusys/ai/）:
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）:
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini）の JSON Mode を利用してバッチ（最大20銘柄/チャンク）でセンチメントを算出。
    - リトライ（レート制限・ネットワーク・5xx）と指数バックオフ、JSON 応答の厳密なバリデーションを実装。
    - スコアのクリッピング（±1.0）、部分成功時の DB 書き込み保護（対象コードのみ DELETE → INSERT）。
    - calc_news_window を提供（JST 時間ウィンドウの UTC 変換）。
    - テスト容易性のため _call_openai_api 等を patch 可能に設計。
    - パブリック関数: score_news(conn, target_date, api_key=None) をエクスポート（ai.__init__.py）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。
    - DB からのデータ取得はルックアヘッドバイアス対策（date < target_date 等）を採用。
    - API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ設計。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - パブリック関数: score_regime(conn, target_date, api_key=None)。
- Research / ファクター計算モジュールを追加（src/kabusys/research/）:
  - factor_research.py:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、MA200 乖離を計算。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials を利用して PER, ROE を算出（EPS=0/欠損は None）。
    - DuckDB を用いた SQL ベースの実装。結果は (date, code) 辞書リストで返す。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None): 各ホライズンの将来リターンを一括取得（デフォルト [1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。
    - rank(values): 同順位処理（平均ランク）を含むランク変換実装。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
  - research.__init__.py で上記関数群と zscore_normalize（kabusys.data.stats から再エクスポート）を公開。
- Data モジュールを追加（src/kabusys/data/）:
  - calendar_management.py:
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを一貫して適用。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィルと健全性チェックを実装。
  - pipeline.py:
    - ETLResult データクラスを定義（取得件数、保存件数、品質問題、エラー収集等）。
    - ETL パイプライン向けの内部ユーティリティ（テーブル存在チェック、最大日付取得等）。
  - etl.py: pipeline.ETLResult を再エクスポート。
- テスト/モックを想定した設計:
  - OpenAI 呼び出し箇所に対して patch 可能（ユニットテストでの差し替えを想定）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 破壊的変更 (Breaking Changes)
- （初版リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーや各種トークンは環境変数から取得する設計（必須チェックあり）。
- .env 自動読み込みはデフォルトで有効。テスト環境などで自動ロードを回避するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すること。

### 注意事項 / 動作上の設計判断
- ルックアヘッドバイアス防止
  - 多くの処理（AI スコア、レジーム判定、ファクター計算）は datetime.today()/date.today() の直接参照を避け、呼び出し側から target_date を明示的に渡す設計になっています。これは将来情報の漏洩（ルックアヘッド）を防ぐための意図的な設計です。
- フェイルセーフ
  - OpenAI API 呼び出し失敗時には例外を投げるのではなく、スコアを 0.0 にフォールバックするなど安全側の挙動を採用（ログ出力あり）。ただし、API キー未指定時は ValueError を送出します。
- DB 書き込みの冪等性
  - market_regime / ai_scores 等への書き込みは既存レコードを削除してから挿入することで冪等性を保つ実装（部分失敗時にも既存の他コードデータを保護する戦略）。
- DuckDB 互換性
  - 一部実装で DuckDB の executemany 空リスト制約や配列バインドの互換性を考慮した回避策を採用。
- API 呼び出しの設計
  - OpenAI の JSON Mode（response_format={"type": "json_object"}）を使用し、応答の厳密な JSON 構造を前提にパース・検証を行う。

### 既知の制限 / 未実装
- PBR や配当利回りなど一部バリューファクターは未実装（calc_value の注記参照）。
- strategy / execution / monitoring の具体実装は本リリースでは未確認（__all__ に列挙のみ）。
- raw_news の本文や外部 API のデータ構造に依存するため、実運用前にデータ整合性の確認が必要。

---

今後のリリースでは、実稼働での運用改善、監視・発注モジュールの実装、テストカバレッジ強化、OpenAI 使用量削減（プロンプトの最適化やキャッシュ）などが想定されます。必要であればこの CHANGELOG を元に追加の細分化（モジュール別の変更ログ）を作成します。