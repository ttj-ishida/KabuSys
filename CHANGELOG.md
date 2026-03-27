# CHANGELOG

すべての注目に値する変更点を記録します。本ファイルは Keep a Changelog に準拠しています。

バージョン、日付はコードベースの初期実装（推測）に基づいて記載しています。

## [0.1.0] - 2026-03-27

概要: 初期リリース。日本株自動売買プラットフォームのコアライブラリを実装。データ取得・ETL、マーケットカレンダー管理、研究（ファクター計算・特徴量探索）、AI を用いたニュース・マクロセンチメント解析、および環境設定ユーティリティを含む。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブパッケージ群のエクスポート: data, research, ai などの主要モジュールを公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を起点）。
  - .env と .env.local の読み込み優先度を実装（OS 環境変数保護・上書き制御を考慮）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - 高度な .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォートのバックスラッシュエスケープ対応、
    - インラインコメント処理（クォートあり/なしの挙動を分離）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス /実行環境（development/paper_trading/live）等のプロパティを安全に取得。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン用の ETLResult データクラス（pipeline.ETLResult を再エクスポート）。
  - pipeline モジュールに差分取得・保存・品質チェックを想定したユーティリティを実装（DuckDB 前提）。
  - calendar_management モジュール:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合の曜日ベースのフォールバック。
    - calendar_update_job により J-Quants からの差分フェッチと冪等保存（バックフィル・健全性チェック含む）。
    - 市場カレンダー未取得時でも一貫した振る舞いを保つ設計。

- AI 関連 (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でバッチセンチメント評価して ai_scores テーブルへ書き込む機能（score_news）。
    - JST ベースのニュースウィンドウ計算（calc_news_window）。
    - チャンク処理（1 API コールあたり最大 _BATCH_SIZE 銘柄）、記事数と文字数のトリム制御。
    - JSON Mode を利用した厳密なレスポンスバリデーションとパース回復処理（前後余計テキストの補正）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
    - DuckDB の executemany の挙動（空リスト不可）への対処。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム判定（score_regime）。
    - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し、スコア合成、冪等な DB 書き込みを実装。
    - API 障害時のフェイルセーフ（macro_sentiment = 0.0）およびリトライロジック。
  - OpenAI 呼び出しは OpenAI SDK を使用し、テスト容易性のため call 関数を patch 可能に設計。

- 研究用ユーティリティ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などのモメンタム系ファクター計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などのボラティリティ/流動性指標。
    - calc_value: raw_financials を使った PER / ROE の算出（target_date 以前の最新財務データを利用）。
    - DuckDB 内で SQL とウィンドウ関数を用いて効率的に計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンに対する将来リターン計算（複数ホライズンを同時に処理）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - rank: 同順位を平均ランクで処理するランク化ユーティリティ。
    - factor_summary: count/mean/std/min/max/median といった統計要約を標準ライブラリで実装。
  - すべての研究モジュールは pandas 等外部依存なしで実装。

### 変更 (Changed)
- （初期リリースのため「変更」は特に無し。実装上の設計上の考慮点を明確化）
  - ルックアヘッドバイアス防止: 各種スコアリング/ETL 関数は datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
  - DuckDB 特性（executemany の空リスト不可、日付型の取り扱い）に合わせた互換性処理を追加。

### 修正 (Fixed)
- （初期リリースのため「修正」は特に無し。ただし、以下のフォールバック/フェイルセーフが実装されている点を記載）
  - OpenAI / ネットワーク障害時に処理を中断させず、フェイルセーフ（macro_sentiment=0.0、該当チャンクのスキップ）で継続する設計を実装。
  - .env 読み込み失敗時に警告を出して処理継続するように変更。

### 注意事項 / 既知の制約 (Known issues and limitations)
- OpenAI API キーは明示的に渡すか環境変数 OPENAI_API_KEY を設定する必要あり（未設定時は ValueError を送出）。
- jquants_client（kabusys.data.jquants_client）や kabu ステーション関連クライアントはインターフェース参照はあるが、この差分には実装詳細が含まれていない可能性がある（実行環境での依存に注意）。
- news_nlp および regime_detector は gpt-4o-mini の JSON mode を前提とした設計。LLM の応答仕様が変わるとパースロジックの調整が必要。
- カレンダー関連は market_calendar が存在しない場合に曜日ベースでフォールバックするため、精密な祝日情報を求める場合は calendar_update_job を定期実行してデータを投入する必要あり。
- 全体は DuckDB を前提とした設計（DuckDB のバージョン差や型挙動に依存する部分あり）。
- タイムゾーン: news ウィンドウ等は UTC naive datetime を使用し、JST を基準に変換している点に注意。

---

将来的なリリースでは、ユニットテストの追加、jquants_client と kabu ステーションの実装/モック、より詳細なエラーレポート、メトリクス収集や CI/CD の導入などが想定されます。必要であれば、この CHANGELOG を基に英語版やさらに細かいリリースノートの作成を支援します。