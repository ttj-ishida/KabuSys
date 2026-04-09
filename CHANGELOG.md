# CHANGELOG

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [Unreleased]
- 次回リリースに向けた作業項目（ドキュメント整備・テスト拡張）を予定。

---

## [0.1.0] - 2026-04-09

初回公開リリース。日本株自動売買システムの基盤機能を実装しています。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。外部公開モジュール: data, strategy, execution, monitoring を想定。
- 環境設定 / 設定管理
  - 環境変数・設定管理モジュール (kabusys.config) を追加。
    - .env / .env.local の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env パースの堅牢化（export 形式、クォート内のエスケープ、行内コメントの扱い等）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / Paper Trading 等の設定プロパティを公開。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値検証（不正値時に ValueError を送出）。
    - pid/kill フラグやリソース閾値など監視用の設定も含む。
- データ関連
  - ETL 結果データクラス ETLResult を公開（kabusys.data.pipeline -> kabusys.data.etl）。
  - ETL パイプライン骨格 (kabusys.data.pipeline):
    - 差分取得・バックフィル・品質チェックを想定した設計。
    - ETLResult に品質問題・エラーの集約と to_dict 変換機能を追加。
  - カレンダー管理モジュール (kabusys.data.calendar_management):
    - JPX カレンダー夜間更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar 未取得時の曜日ベースのフォールバック。
    - 最大探索日数やバックフィル、健全性チェックの実装。
- 研究（Research）機能
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離等の計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等の計算。
    - calc_value: PER/ROE（raw_financials と prices_daily の組合せ）。
    - DuckDB 上の SQL+ウィンドウ関数を用いた実装（ルックアヘッドバイアス対策、欠損ハンドリング）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（例: 1,5,21 営業日）に対する将来リターン算出（複数ホライズン一括取得）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - rank: 同順位の平均ランク処理（丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
  - kabusys.research パッケージエクスポートを整備。
- AI / ニュースNLP
  - ニュースセンチメント解析モジュール (kabusys.ai.news_nlp):
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して銘柄ごとの ai_score を ai_scores に書き込む。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく集計ロジック（UTC 変換済み）。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大対策（記事数/文字数トリム）。
    - OpenAI（gpt-4o-mini）への JSON Mode 呼び出し、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - 再試行（429/ネットワーク/タイムアウト/5xx）と指数バックオフ、失敗時は安全にスキップ。
    - DuckDB executemany の空リスト回避（互換性対応）。
  - 市場レジーム判定モジュール (kabusys.ai.regime_detector):
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して market_regime に書き込み。
    - マクロニュース抽出（マクロキーワード群）→ OpenAI 呼び出し（gpt-4o-mini、JSON）→ スコア合成・ラベリング（bull/neutral/bear）。
    - LLM 呼び出しの堅牢化（リトライ・フォールバック macro_sentiment=0.0）。
    - ルックアヘッドバイアス対策（target_date 未満のデータのみ使用、datetime.today を参照しない）。
  - テスト容易性のため OpenAI 呼び出し関数を関数化しパッチ可能に設計。
- テスト/実装支援
  - JSON パースの回復処理（前後余計なテキストが混入した場合に最外の {} を抽出して再パース）。
  - OpenAI SDK の例外種別（RateLimitError, APIConnectionError, APITimeoutError, APIError）への対応。
  - DuckDB 型変換ユーティリティ（日付変換）やテーブル存在チェックを実装。

### 変更 (Changed)
- 初期リリースのため特定の「変更」はなし（基盤実装としての初出）。

### 修正 (Fixed)
- 初期リリースのため特定の「修正」はなし。ただし以下の安定化処理を含む実装上の配慮:
  - .env 読み込み失敗時のワーニング出力（例外非透過）。
  - DB 書き込みでのトランザクション保護（BEGIN/COMMIT/ROLLBACK と ROLLBACK 失敗時の警告ログ）。
  - DuckDB executemany に対する空リスト回避。

### セキュリティ (Security)
- 外部 API キー（OpenAI 等）は環境変数または明示的引数で注入し、未設定時は ValueError で明示的に失敗する設計。

### 既知の注意点 / 設計方針
- ルックアヘッドバイアス防止のため、内部処理は datetime.today() / date.today() 参照を避け、明示的に target_date を受け取る API を採用。
- API 呼び出し失敗時はフェイルセーフ（スコア 0 やスキップ）で継続する設計。部分失敗時に既存データを消さない（コードを絞った DELETE → INSERT を利用）。
- DuckDB のバージョン差異を考慮した互換性処理を含む（executemany / list バインド等）。
- jquants_client 等、外部データ取得用クライアントは別モジュールとして分離（このリポジトリ内で参照）。

---

今後の予定（例）
- strategy / execution / monitoring の具体実装・統合テスト追加。
- モニタリング周り（プロセス管理、アラート）のドキュメント整備。
- CI・テストケースの拡充（OpenAI 呼び出しのモックを用いた単体テスト等）。

--------------------------------
（記載はソースコードの実装内容・コメント・設計メモから推測して作成しています。実際の変更履歴やリリースノートはプロジェクト運用ポリシーに合わせて調整してください。）