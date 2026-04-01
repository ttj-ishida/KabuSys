CHANGELOG
=========
（このファイルは Keep a Changelog 準拠の書式で作成されています）

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - 基本パッケージ情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - __all__ で公開モジュール: data, strategy, execution, monitoring（エントリポイントを公開）

- 設定 / 環境変数管理（kabusys.config）
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）
  - .env / .env.local 自動読み込み（優先順: OS 環境変数 > .env.local > .env）
  - .env パーサーを実装:
    - コメント行・export KEY=val 形式・クォート／エスケープ対応
    - クォートなしでの行内コメント（# 前がスペース/タブ の場合）を考慮
  - 自動ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - 必須環境変数取得用の _require と Settings クラスを提供
  - 各種設定プロパティを提供（J-Quants, kabuステーション, Slack, DB パス, 監視閾値, ログレベル, env 判定等）
  - 設定値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news + news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出して ai_scores へ書き込み
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）
    - バッチ処理（1 回で最大 20 銘柄）・トークン肥大化対策（記事数と文字数の上限）
    - API 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx を指数バックオフで再試行）
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット、コード整合性、数値変換、±1.0 でクリップ）
    - 部分成功を考慮した DB 更新（取得できたコードのみ DELETE → INSERT）
    - テスト容易性のため _call_openai_api の差し替えを想定

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）判定
    - マクロ記事抽出用キーワードリストと最大記事数を設定
    - OpenAI 呼び出しに対する再試行・フェイルセーフ（API 失敗時は macro_sentiment = 0.0）
    - レジームスコアを market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を参照しない、prices_daily は target_date 未満のデータのみを利用）

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を優先して営業日判定を行う is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 実装
    - DB 未登録日は曜日ベースのフォールバック（週末を非営業日扱い）
    - 夜間バッチジョブ calendar_update_job を実装（J-Quants から差分取得・バックフィル機能・健全性チェック・保存）
    - 最大探索日数制限やバックフィル設定、DB 値優先の一貫した振る舞いを確保

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入（取得/保存件数、品質問題、エラー情報を集約）
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client / quality モジュールと連携）
    - DuckDB 周りの互換性配慮（executemany に空リストを渡さない等）
    - _table_exists / _get_max_date 等のユーティリティを実装（注：実装中の未完成箇所あり。詳細は Known issues を参照）

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、ma200乖離）
    - ボラティリティ / 流動性（20日 ATR、相対 ATR、20日平均売買代金・出来高比）
    - バリュー（PER、ROE）を実装
    - DuckDB SQL を用いた計算（prices_daily / raw_financials に依存）
    - データ不足時は None を返す挙動を採用

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、柔軟な horizons 指定、入力検証）
    - IC（Information Coefficient）計算（スピアマンの順位相関）
    - ランク変換ユーティリティ（rank、同順位は平均ランク）
    - 統計サマリー（count/mean/std/min/max/median）を提供
    - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装

Changed
- 初版の実装ではあるが、運用での堅牢性（フェイルセーフ、ログ、リトライ、DB トランザクション）を重視して設計

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details
- OpenAI API
  - 使用モデル: gpt-4o-mini（JSON Mode を利用）
  - API キーは関数引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出する設計（利用者はキー管理に注意）
  - テストしやすいように _call_openai_api を個別にモックすることを想定

- DuckDB / SQL 周りの互換性注意点
  - DuckDB バージョンによるバインド挙動の差（executemany に空リスト渡せない等）に配慮した実装
  - DB 書き込みは冪等性を確保（DELETE → INSERT）し、部分失敗時に既存データを保護

Known issues / TODO
- pipeline._get_max_date の実装ファイル末尾が途中で切れており（"return date.fro" のような不完全行）、現状では構文エラー / 実行時エラーを引き起こす可能性があります。リリース前に該当関数の完了実装が必要です。
- src/kabusys/data/__init__.py は空のまま（将来的にサブモジュール公開を整理する必要あり）。
- jquants_client、quality モジュールは本スニペットでは外部依存扱い（呼び出し箇所あり）。それらの実装またはモックが必要。
- monitoring / strategy / execution の実装は本スニペットで確認できないため、公開 API と実装の整合性を確認してください。
- OpenAI 呼び出し時のレスポンスが JSON モードでも不正な場合を保護するためのパース耐性はあるが、実運用で Edge ケースの追加ハンドリング（出力整形やより詳細なログ）が必要な場合があります。
- テストカバレッジ（特に DuckDB を用いる SQL 部分および OpenAI API とのやり取り）は十分に整備することを推奨します。

ライセンス / Contributing
- このリリース候補にはライセンス情報や貢献ガイドが含まれていないため、プロジェクト配布前に LICENSE と CONTRIBUTING 文書の追加を推奨します。