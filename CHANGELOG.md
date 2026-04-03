CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。
日付は yyyy-mm-dd 形式で記載します。

[Unreleased]
-------------

（現在なし）

[0.1.0] - 2026-04-03
-------------------

Added
- 初回リリース: kabusys パッケージの基本機能群を追加。
  - パッケージ情報
    - src/kabusys/__init__.py にてパッケージ名とバージョン（0.1.0）を定義。
  - 設定・環境変数管理（src/kabusys/config.py）
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - export KEY=val、シングル/ダブルクォート、エスケープ、インラインコメント等の .env 構文を堅牢にパースする実装。
    - OS 環境変数の保護（protected set）と override フラグによる上書き制御。
    - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / システム環境（KABUSYS_ENV, LOG_LEVEL 等）をプロパティで取得。値検証と既定値を実装。
    - PID ファイル・キルフラグ等、監視実行に必要な設定を含む。
  - AI モジュール（src/kabusys/ai）
    - ニュース NLP（src/kabusys/ai/news_nlp.py）
      - raw_news と news_symbols を集約して銘柄ごとのニュースをまとめ、OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（ai_scores）を算出・書込み。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算する calc_news_window。
      - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事数・文字数上限の実装（トークン肥大化対策）。
      - JSON mode を利用したレスポンスのバリデーションと復元ロジック（余分な前後テキスト対応）。
      - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。失敗時はフェイルセーフでスキップ（例外を上げない）。
      - テスト用フック: _call_openai_api をパッチ可能にしてユニットテストを容易化。
    - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
      - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini・JSON mode）、および API リトライ/フォールバック（失敗時 macro_sentiment=0.0）。
      - ルックアヘッドバイアス防止（date < target_date 等）設計。
  - リサーチ（src/kabusys/research）
    - ファクター計算（src/kabusys/research/factor_research.py）
      - モメンタム: mom_1m/mom_3m/mom_6m、および ma200_dev（200日移動平均乖離率）。
      - ボラティリティ/流動性: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、出来高比率等。
      - バリュー: PER（株価/EPS）、ROE（raw_financials からの取得）。
      - 各関数は DuckDB を用いた SQL＋Python 実装で、prices_daily / raw_financials のみ参照。データ不足時は None を返す等の堅牢な取り扱い。
    - 特徴量探索（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算（calc_forward_returns）：複数ホライズンを一度に計算、入力検証あり。
      - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を実装（同順位は平均ランク）。
      - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）。
      - pandas 等に依存せず標準ライブラリのみで実装。
    - 研究用ユーティリティの再エクスポート（zscore_normalize など）。
  - データプラットフォーム（src/kabusys/data）
    - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
      - market_calendar テーブルを利用した営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
      - DB 登録値優先、未登録日は曜日ベースでのフォールバックを一貫して適用。
      - 夜間バッチ更新 job（calendar_update_job）: J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存。
    - ETL パイプライン（src/kabusys/data/pipeline.py）
      - ETL 処理の設計に基づく差分取得、保存（jquants_client の save_* を利用して冪等）、品質チェック（quality モジュール）を想定したインターフェース。
      - ETLResult dataclass を導入し、取得数・保存数・品質問題・エラー情報を構造化して返却。
      - デフォルトのバックフィル日数やカレンダー先読みなどの定数を定義。
    - ETL 公開インターフェースの再エクスポート（src/kabusys/data/etl.py）。
    - DuckDB を主要なストレージとして使用（クエリ形態・埋め込み SQL に最適化）。
  - 設計上のガイドライン・品質面の強化
    - ルックアヘッドバイアス防止の徹底（datetime.today()/date.today() を直接参照しない局所設計）。
    - DB 書込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定）。
    - OpenAI 呼び出しは JSON mode を利用して機械的に解析しやすくし、リトライ・フォールバックを明確に実装。
    - テストの容易化（内部 API 呼び出しの差し替えポイントを確保）。
    - 例外処理とログ出力を充実させ、失敗時もシステムを破綻させないフェイルセーフ設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 備考
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY で注入可能。未指定時は ValueError を返す設計。
- .env の自動読み込みはプロジェクト配布後も動作するよう、__file__ を基点にルートを探索する実装になっている。テスト時に自動ロードを無効化する環境変数が利用可能。
- DuckDB のバージョン差異（executemany と空リスト等）に配慮した防御的実装を行っている。

今後の予定（想定）
- ai モジュールの学習済みモデルの差し替えや追加、パフォーマンス改善（並列化等）。
- pipeline の具体的な ETL 実装（jquants_client の詳細な統合）と品質チェックルールの拡充。
- 監視・運用機構（プロセス管理、アラート連携）の追加強化。