CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このファイルはリポジトリ内のコード内容から推測して作成した推定の変更履歴です。

フォーマット
-----------

各バージョンは日付付きで記載し、カテゴリは Keep a Changelog の推奨（Added, Changed, Fixed, Deprecated, Removed, Security）に従います。

Unreleased
----------

- なし（開発中の変更はここに列挙してください）

[0.1.0] - 2026-03-31
--------------------

Added
- 初期公開リリース: kabusys パッケージ (バージョン 0.1.0)
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 設定・環境変数管理
  - robust な .env 自動読み込み機能を追加（プロジェクトルートは .git 又は pyproject.toml を基準に探索）。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを実装し、J-Quants・kabu API・Slack・DBパス・監視閾値・環境/ログレベル等をプロパティとして提供（バリデーション含む）。
  - 無ければ ValueError を送出する必須キー取得ユーティリティ _require を提供。

- AI（自然言語処理）機能
  - ニュースセンチメント（news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）の JSON mode でバッチ評価。
    - 1チャンク最大20銘柄、銘柄ごとのトークン制御（記事最大数・文字数制限）。
    - 429 / ネットワーク断 / タイムアウト / 5xx 対応の指数バックオフによるリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の検証）、スコアは ±1.0 にクリップ。
    - スコア書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等性と部分失敗耐性を確保。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（ユニットテストで patch 可能）。

  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で regime_label（bull/neutral/bear）を算出。
    - マクロニュース抽出はキーワードフィルタ（日本・米国等のマクロ語彙）に基づく。記事が無ければ LLM 呼び出しをスキップして macro_sentiment=0.0。
    - OpenAI 呼び出しはリトライ・バックオフを実装し、最終的にフォールバックで 0.0 を採るためフェイルセーフ設計。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB エラー時は ROLLBACK を試行して例外を上位へ伝播。

- データプラットフォーム（Data）
  - ETL パイプライン基盤（pipeline モジュール）
    - 差分更新・バックフィル・品質チェックを想定した設計。ETLResult データクラスを公開（保存件数・品質問題・エラー集約等）。
    - J-Quants クライアント経由の取得 → save_* による冪等保存（ON CONFLICT 想定）を想定。
    - 品質チェックは問題を収集して戻す（即時中断しない設計）。

  - カレンダー管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定ユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先、未登録日は曜日ベースのフォールバック。DB がまばらでも一貫した判定を行う実装。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・健全性チェック（未来日付の異常検出）を実装。

- リサーチ（research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR、出来高・売買代金指標）、Value（PER, ROE）を DuckDB SQL ベースで計算。
    - データ不足（行数不足等）を考慮して None を返す設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）、ランク付け、ファクター統計サマリを実装。
    - 外部ライブラリに依存しない純 Python 実装。

- その他
  - データモジュールの公開調整（data.etl で ETLResult の再エクスポート等）。
  - 各所で DuckDB を使用。SQL による処理と Python ロジックの組合せで実装。

Fixed
- DuckDB に対する executemany の空リスト投げ込み問題に配慮（空リストの場合は実行をスキップ）して互換性を確保。
- OpenAI API レスポンスパース失敗や API の一時エラー時に例外を上位に投げず、フォールバック（score=0.0、空スコア辞書等）することで処理全体の耐障害性を向上。

Security
- Settings における KABUSYS_ENV / LOG_LEVEL の値検証を実装し、不正な値は ValueError で早期検出する。

Notes / Design decisions
- ルックアヘッドバイアス対策: いずれの処理も datetime.today() / date.today() を内部で直接参照せず、呼び出し側が target_date を指定する設計。
- テスト容易性: OpenAI 呼び出し箇所はモジュール内プライベート関数を patch して差し替え可能にしている（ユニットテストが可能）。
- フェイルセーフ設計: 外部 API 失敗時は代替値で継続（例: macro_sentiment=0.0、スコア取得失敗銘柄はスキップ）し、部分失敗が他のデータを破壊しないよう DB 書き込みは制限的に行う。
- 依存関係: 実行には DuckDB と OpenAI SDK（および J-Quants クライアント等）が必要。DB スキーマや外部 API の存在が前提。

Acknowledgements
- この CHANGELOG はリポジトリ内コードを解析して作成した推定の変更履歴です。実際のコミット履歴やリリースノートが存在する場合はそれに従ってください。

[0.1.0]: # (初期リリース: 2026-03-31)