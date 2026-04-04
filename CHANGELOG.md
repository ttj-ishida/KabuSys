# CHANGELOG

すべての重要な変更をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新リリース
=============

[0.1.0] - 2026-04-04
-------------------

Added
- 初回公開: KabuSys 日本株自動売買システムの基盤機能を実装。
- パッケージ初期化:
  - src/kabusys/__init__.py にてパッケージの公開モジュールを定義。
  - バージョン番号を "0.1.0" として設定。
- 環境設定:
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定読み込みを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない自動ロードを実現。
    - .env/.env.local の読み込み順序（OS環境変数 > .env.local > .env）と上書き制御を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
    - export KEY=val 形式、引用符付き値、インラインコメントの扱いなどを考慮した堅牢な .env パーサーを実装。
    - 保護キー（既存 OS 環境変数）を上書きしない仕組みを実装。
    - Settings クラスを提供し、アプリケーション設定（API トークン、DB パス、監視設定、ログレベル、環境種別など）をプロパティ経由で取得可能に。
- AI（自然言語処理）:
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を OpenAI（gpt-4o-mini）の JSON Mode でバッチ解析し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）機能を提供（calc_news_window）。
    - バッチ処理、銘柄毎のトリミング（記事数/文字数制限）、レスポンス検証、スコアクリップ（±1.0）、リトライ（429/ネットワーク/タイムアウト/5xx の指数バックオフ）を実装。
    - レスポンス整形・バリデーション機能（_validate_and_extract）とチャンク単位の処理（_score_chunk）を実装。
  - src/kabusys/ai/regime_detector.py
    - ETF（1321）の 200 日移動平均乖離（重み 70%）とニュース由来 LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする機能を実装（score_regime）。
    - マクロニュース抽出、OpenAI 呼び出し（JSON Mode）、リトライ／バックオフ、API エラー時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - 先行バイアス防止のため datetime.today()/date.today() を直接参照しない設計。
- データ基盤（Data Platform）:
  - src/kabusys/data/pipeline.py
    - ETL パイプライン基盤を実装。差分取得、保存（idempotent）、品質チェックの枠組みを提供。
    - ETL 実行結果を表現する dataclass ETLResult を実装（to_dict により品質問題を辞書化）。
  - src/kabusys/data/etl.py
    - ETLResult の公開再エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）の操作および夜間バッチ更新処理（calendar_update_job）を実装。
    - 営業日判定、前後営業日の検索、期間内営業日の取得、SQ 日判定などのユーティリティを提供。
    - DB データが欠けている場合は曜日ベースのフォールバック（週末を非営業日と判断）を行い、一貫性のある振る舞いを保証。
    - API 取得 → 保存の冪等処理・バックフィル・健全性チェックを実装。
- リサーチ／ファクター群:
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M・MA200乖離）、ボラティリティ（ATR20）、流動性（20日平均売買代金等）、バリュー（PER/ROE）などファクター計算関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB 上で SQL とウィンドウ関数を用いて高効率に計算する設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純標準ライブラリ＋DuckDB 実装。
  - src/kabusys/research/__init__.py
    - 主要なリサーチ API を公開。
- データアクセスに DuckDB を利用する設計を採用し、既存テーブル（prices_daily / raw_news / ai_scores / market_regime / raw_financials / news_symbols 等）を前提に実装。

Changed
- 設計上の重要な方針を明確化:
  - すべての「日付基準」処理は内部で外部から与えた target_date を用い、現在時刻参照を避けてルックアヘッドバイアスを防止。
  - OpenAI 呼び出しはモジュール毎に独立実装（テスト用に patch 可能）としてモジュール結合を低減。
  - DB 書き込みは冪等性とトランザクション（BEGIN/DELETE/INSERT/COMMIT）を意識した実装。
  - DuckDB に起因する制約（executemany の空リスト不可など）へ対応するためのガード実装を追加。
  - API 呼び出し失敗時は例外を直接伝播させず、フェイルセーフ（スコア 0 やスキップ）で継続する箇所を明示。

Fixed
- 環境変数読み込み時の堅牢性強化:
  - .env 読込失敗時に警告を出して処理を継続するよう改善。
  - export プレフィックス、引用符付き値、エスケープ、インラインコメント等の扱いを明確化して実装し、誤パースを軽減。
- OpenAI レスポンスのパース耐性を向上:
  - JSON mode で稀に前後に余分なテキストが混入するケースに対して最外の {} を抽出して復元するフォールバックを追加。
  - レスポンスのキー・型チェックを厳格化し、不正レスポンスはスキップするよう変更。
- DuckDB 周辺の互換性処理:
  - テーブル存在チェックや DuckDB 返り値の date 変換ユーティリティを追加し、未作成テーブルや NULL 値に対する堅牢性を向上。

Security
- 環境変数の取扱いにおいて、OS 環境変数をデフォルトで保護（.env による不注意な上書きを防ぐ）する実装を導入。

Notes / Implementation details
- OpenAI クライアントは openai.OpenAI を利用（gpt-4o-mini, JSON Mode）。API キーは関数引数または環境変数 OPENAI_API_KEY で指定可能。
- API リトライは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで実施。その他の APIError は非再試行として扱う方針。
- 市場レジーム判定では ETF 1321（Nikkei 225 連動）を代表指標として使用し、MA200 乖離とマクロニュースセンチメントを合成して -1.0〜1.0 のスコアを作成。
- ai_scores / market_regime への書き込みは「部分失敗時に既存データを不必要に消さない」ことを意識して、対象コードの絞り込み DELETE → INSERT の手順を採用。

未対応 / 今後の予定（Todo）
- strategy / execution / monitoring モジュールの実装（パッケージ __all__ に記載済みだが、現時点では実装が含まれていないファイルあり）。
- より詳細な品質チェックルールや自動テスト（特に OpenAI 呼び出しのモック・DB 統合テスト）の整備。
- docs / 使用例・API リファレンスの充実。

過去のリリース
----------------
（初回リリースのため履歴なし）