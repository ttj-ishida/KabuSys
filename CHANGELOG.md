# Changelog

すべての変更は Keep a Changelog の仕様（https://keepachangelog.com/ja/1.0.0/）に従って記載しています。  
このプロジェクトの初期リリースを以下にまとめます。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティ群をパッケージ化しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期公開。__version__ = 0.1.0、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定管理（kabusys.config）
  - .env ファイル・環境変数読み込みユーティリティを実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサは以下をサポート:
    - コメント行・空行の無視、`export KEY=val` 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ扱い
    - クォートなし時のインラインコメント処理（直前が空白/タブの場合のみ）
    - 読み込み失敗時の警告発行
  - 必須設定の取得ヘルパー `_require` と、環境値検証（KABUSYS_ENV, LOG_LEVEL）の実装。
  - DBファイルのデフォルトパス（DuckDB/SQLite）設定の提供。
  - settings オブジェクトを公開（J-Quants / kabu API / Slack 等の設定プロパティを含む）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）によりカレントディレクトリに依存しない自動ロードを実現。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理機能（market_calendar テーブル操作、営業日判定ユーティリティ）を実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB にデータがない場合は曜日（週末）ベースでフォールバックする一貫したロジック。
    - calendar_update_job により J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック含む）を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約: 取得数/保存数/品質問題/エラー等）。
    - 差分更新・バックフィル・品質チェックを想定した ETL パイプラインの土台を実装（jquants_client 経由の取得/保存、品質チェックフック想定）。
    - DB テーブル存在チェックや最大日付取得等のユーティリティ関数を実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- ニュース NLP / AI（kabusys.ai）
  - news_nlp:
    - raw_news / news_symbols をソースに、銘柄毎のニュースを集約して OpenAI（gpt-4o-mini）でセンチメント評価を行い ai_scores テーブルへ書き込む機能（score_news）を実装。
    - 処理の特徴:
      - ニュースウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB と照合）
      - 1銘柄あたりの記事上限 (_MAX_ARTICLES_PER_STOCK) と文字数上限 (_MAX_CHARS_PER_STOCK) を導入してトークン肥大化を防止
      - 最大バッチサイズでチャンク化して API コール（デフォルト 20 銘柄／回）
      - OpenAI の JSON Mode を利用し、応答検証・復元ロジックを実装（前後余計なテキストが混ざるケースに対応）
      - レート制限・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ、その他はスキップして継続（フェイルセーフ）
      - レスポンス検証により未知コードの無視、スコアの数値検証、±1.0 でクリップ
      - DuckDB の executemany 特性に配慮した部分置換（DELETE → INSERT）で冪等性と部分失敗時の保護を実現
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - 処理の特徴:
      - ma200_ratio を DuckDB から取得（target_date 未満のデータのみ利用しルックアヘッドを防止）
      - マクロキーワードに基づく raw_news 抽出（最大件数を制限）
      - OpenAI 呼び出しは独立実装、JSON パース・リトライ・フェイルセーフあり（失敗時 macro_sentiment=0.0）
      - 結果を market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等的に書き込み。失敗時は ROLLBACK と再送出。
    - 意図的に datetime.today()/date.today() を参照せず、外部から target_date を与える設計でルックアヘッドバイアスを防止。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金・出来高比を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS 0/欠損時は None）。
    - SQL + DuckDB を用いて、営業日ベースの窓処理・欠損ハンドリングを実装。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用、ホライズン検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。データ不足時は None。
    - rank: 同順位は平均ランクを採るランク化実装（丸めで ties 判定安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。
    - すべて標準ライブラリのみで実装、外部依存を避ける設計。
  - 研究ユーティリティの一部をトップレベルで再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY を期待し、未設定時には ValueError を発生させ明示的にエラーとすることで誤動作を防止。

### Notes / 開発上の設計ポリシー
- ルックアヘッドバイアス防止: AI スコアリング（news/regime）・ファクター計算・ETL 等、全ての時間ベース処理は内部で datetime.today()/date.today() を参照せず、外部から target_date を与える設計。
- フェイルセーフ重視: 外部 API が失敗しても例外を全面的に投げずにフォールバック（0.0 スコアやスキップ）して処理を継続する箇所がある。DB 書き込みはトランザクションで保護し、部分失敗時の既存データ保護に配慮。
- テスト容易性: OpenAI 呼び出しや .env 読み込みを patch で差し替えられるよう設計（ユニットテストを想定）。
- 外部依存: AI 呼び出し以外は DuckDB と標準ライブラリを中心に実装。pandas 等の大型依存は導入していない。

---

将来的に API の安定化、追加のファクタ・指標、strategy / execution / monitoring の実装を予定しています。必要であればリリースノートの形式や詳細レベルは調整します。