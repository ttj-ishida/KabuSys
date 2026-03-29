# Changelog

すべての重要な変更点を本ファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

最新変更
---------

### [Unreleased]
（現時点で未リリースの変更はありません）

過去のリリース
---------------

### [0.1.0] - 2026-03-29
初回リリース。本リポジトリのコア機能群を実装しています。

Added
- パッケージ基盤
  - kabusys パッケージを追加。公開モジュールとして data, strategy, execution, monitoring をエクスポート（__all__）。
  - バージョン情報: 0.1.0（src/kabusys/__init__.py）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して特定（CWD非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数は保護（上書き抑制）される仕組みを実装。
  - 柔軟な .env パーサ:
    - export KEY=val 形式、シングル/ダブルクォート対応、バックスラッシュエスケープ、インラインコメント処理等をサポート。
  - 必須設定チェック（_require）と各種プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の取得。
    - デフォルト値対応: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値の明示）。
    - is_live / is_paper / is_dev の便利プロパティ。

- AI（自然言語処理）機能（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチで送信して銘柄単位のセンチメント（-1.0〜1.0）を算出。
    - 時間ウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して処理。
    - バッチサイズ、記事数・文字数上限（トークン対策）、API リトライ（429/ネットワーク断/5xx）を実装。
    - レスポンスの厳密なバリデーションとスコアのクリップ、部分成功時の DB 書き込み保護（取得済コードのみ DELETE→INSERT）。
    - テスト容易性のため _call_openai_api をモック差替え可能に実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組合せて日次で市場レジーム（bull/neutral/bear）を算出。
    - ニュース抽出はマクロキーワードに基づき raw_news から取得、LLM 呼出は gpt-4o-mini を利用して JSON 出力を期待。
    - API 再試行、サーバーエラーの扱い、フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト時に差し替え可能な _call_openai_api を使用。

- データプラットフォーム（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB 登録がない日については曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - 夜間バッチ更新 job (calendar_update_job): J-Quants API から差分取得し冪等保存、バックフィルと健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得・保存・品質チェックフローの下地を実装。
    - ETLResult データクラスを定義（pipeline モジュールを etl.py で再エクスポート）。
    - DB 最終取得日の判定、バックフィル、品質チェック結果の集約、エラー/品質フラグ保持をサポート。
    - jquants_client 経由の保存、品質検査モジュール quality との連携を想定。
  - その他
    - データ関連のユーティリティ（テーブル存在判定、日付変換等）。

- リサーチ / ファクター解析（src/kabusys/research）
  - factor_research.py:
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日ATR, 相対ATR）、Value（PER, ROE）、Liquidity（20日平均売買代金, 出来高比率）などのファクター計算実装。
    - DuckDB 上で SQL を用いて効率的に計算。データ不足時の None 処理を明確に扱う。
  - feature_exploration.py:
    - 将来リターン算出（calc_forward_returns）: 任意ホライズンに対応、ホライズン検証と1クエリでの取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関の実装（同順位は平均ランク）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）。
  - research パッケージの公開 API を整理（__init__ にて主要関数をエクスポート）。

Changed
- （該当なし）初回リリースのため既存リリースからの変更はありません。

Fixed
- （該当なし）初回リリースのためバグ修正履歴はありません。

Security
- （該当なし）

設計上の重要な注意点（ドキュメント的メモ）
- ルックアヘッドバイアス回避: 各種処理で datetime.today() / date.today() を直接参照しない設計（関数引数で対象日を受け取る）。
- DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT を想定）し、部分失敗時に既存データを過剰に消さない設計。
- OpenAI 呼び出しは JSON Mode を利用し、エラーハンドリングと再試行を明確化。テストのためモック差替え可能なポイントを提供。
- 外部依存は最小限（duckdb と OpenAI SDK を想定）。リサーチ周りは標準ライブラリのみで実装する方針。

既知の制限 / 将来の改善候補
- 現バージョンでは一部ファクター（PBR・配当利回り等）は未実装。
- DuckDB バインドの互換性（executemany の空リスト等）への注意点を実装で考慮済みだが、環境差異で追加対応が必要になる可能性あり。
- OpenAI API のモデルやレスポンス形式の変化に対する互換性確保は今後の改善項目。

Contributors
- 初回実装（コードベース中の著者情報は明示されていません）。README / CONTRIBUTORS ファイルで詳細を追記推奨。

---

注: 上記はリポジトリ内のソースコードから推測して作成した変更履歴です。実際のコミット履歴やリリースノートが存在する場合は、それに合わせて更新してください。