# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

全般的な注記:
- 本リポジトリは日本株のデータ基盤・リサーチ・AI によるニュースセンチメント解析・市場レジーム判定・ETL/カレンダー管理を含むパッケージです。
- DuckDB を用いたローカルデータベース操作と OpenAI（gpt-4o-mini）を想定した JSON Mode の呼び出しを行う実装が含まれます。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-04
### Added
- パッケージ初期リリース。パッケージ名: kabusys、バージョン: 0.1.0
  - src/kabusys/__init__.py にパッケージメタを追加（__version__, __all__）。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートの検出ロジック（.git または pyproject.toml を探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化のサポート。
  - .env パーサーの実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理。
    - キー上書き制御 (override / protected)。
  - 各種設定プロパティ（J-Quants、kabu API、LINE、DB パス、監視閾値、環境/ログレベル検証等）。
  - 必須環境変数未設定時に ValueError を送出する _require 関数。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を入力に、銘柄ごとのセンチメントを OpenAI JSON Mode（gpt-4o-mini）で解析し ai_scores テーブルへ書き込む機能を実装。
    - ニュースウィンドウ計算 (calc_news_window): JST の前日 15:00 ～ 当日 08:30 を UTC で表現。
    - バッチ処理（最大 20 銘柄／API 呼び出し）、トークン肥大化対策（記事数・文字数上限）を実装。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンス検証機能 (_validate_and_extract) により JSON の回復処理、型検査、未知コード無視、スコアのクリップを実装。
    - トランザクション的に DELETE → INSERT を行い、部分失敗時に既存スコアを無駄に消さない保存ロジック。
    - テスト容易化のため _call_openai_api をモジュール内で独立実装し patch 可能に。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し日次で regime（bull/neutral/bear）判定。
    - ma200_ratio 計算時はルックアヘッドバイアスを避けるため target_date 未満のデータのみ使用。
    - マクロキーワードで raw_news をフィルタし、LLM による JSON レスポンスをパースして macro_sentiment を取得。
    - API の失敗やパースエラー時には macro_sentiment=0.0 とするフェイルセーフ。
    - レトライや 5xx の扱い、ログ出力、冪等な market_regime への書込み（BEGIN/DELETE/INSERT/COMMIT）を実装。

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた JPX カレンダー管理機能（営業日判定・次/前営業日・期間内営業日取得・SQ判定）。
    - DB が未取得または値が NULL の場合の曜日ベース（週末除外）フォールバックを実装し、一貫した振る舞いを確保。
    - カレンダー更新ジョブ（calendar_update_job）: J-Quants API から差分取得し冪等保存、バックフィルと健全性チェック（未来日付の検査）を実装。
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスの追加（取得数・保存数・品質問題・エラー集約・シリアライズ機能）。
    - 差分更新、バックフィル、品質チェックの方針とユーティリティを実装（jquants_client/quality 統合を想定）。
    - etl モジュールで ETLResult を再エクスポート。
  - jquants_client との連携を想定した保存・取得処理のフック（実装は jquants_client 側）。

- リサーチ / ファクター (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、流動性指標（20 日平均売買代金・出来高比）や Value（PER/ROE）を DuckDB SQL を用いて計算。
    - データ不足時の None ハンドリングやロギングを実装。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部ライブラリに依存せず、純粋 Python + DuckDB で実装。
  - research パッケージの __all__ に主要関数をエクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を参照する方式。未設定時は明示的に ValueError を投げて誤動作を防止。

### Notes / Implementation details
- すべての日付処理は日付型（date / datetime）で行い、ルックアヘッドバイアスを避ける設計方針を採用。
- 多くの DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 相当）しているため、再実行耐性がある設計。
- OpenAI 呼び出しは各モジュールで独立した _call_openai_api を持たせ、モジュール間の内部関数共有を避け、テストで差し替えやすくしている。
- DuckDB における executemany の仕様に配慮し、空リストバインドを避けるガードを実装。
- 各所で詳細なログ出力（info/debug/warning/exception）を行うようにしており、運用時のトラブルシューティングを支援。

---

該当コードや機能の追加・仕様に関して不明点があれば、どのモジュール／関数の変更履歴を詳細化したいか指示してください。必要に応じてリリースノートを英語版やより詳しい技術注記付きで生成できます。