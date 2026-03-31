Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開内容（__all__）: data, strategy, execution, monitoring（モジュール群の公開インターフェースを定義）

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装
    - プロジェクトルート判定: .git または pyproject.toml を基準に探索（CWD に依存しない）
    - ロード順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）
    - .env.local は .env を上書き（override=True）、ただし OS 環境変数は保護（protected set）
  - .env パーサ実装
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート
    - 行末コメントの取り扱い（クォート外かつ '#' の直前が空白/タブの場合をコメントと判定）
  - 必須環境変数取得関数 _require と Settings クラスを提供
    - J-Quants, kabuステーション, Slack, DB パス 等の設定プロパティを実装
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）の値検証
    - is_live / is_paper / is_dev の利便性プロパティ

- データプラットフォーム・ETL (kabusys.data.pipeline, etl)
  - ETLResult データクラスを公開（to_dict による品質問題の構造化出力含む）
  - 差分更新、バックフィル、品質チェックの設計を実装
  - DuckDB の仕様差（executemany に空リスト渡せない等）への互換性考慮を導入
  - テーブル存在チェック、最大日付取得ユーティリティを実装

- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダーの夜間バッチ更新処理 calendar_update_job を実装
    - J-Quants API から差分取得、ON CONFLICT DO UPDATE 相当の冪等保存
    - バックフィル日数、先読み日数、健全性チェック（極端に未来の日付はスキップ）
  - 営業日判定ユーティリティを多数実装
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar が未取得または未登録日の場合は曜日日ベースでフォールバック（週末除外）
    - 最大探索上限 _MAX_SEARCH_DAYS による無限ループ防止
  - DB 値優先だが未登録日は一貫したフォールバックロジックで補完

- 研究用ファクター計算 (kabusys.research)
  - factor_research: Momentum / Volatility / Value の計算を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPS=0 は None）
    - DuckDB のウィンドウ関数を用いた SQL ベース実装（外部 API にアクセスしない）
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターン計算（LEAD で実装）
    - calc_ic: スピアマンのランク相関（IC）計算（同順位は平均ランク）
    - factor_summary: count/mean/std/min/max/median の統計要約
    - rank: 同順位を平均ランクにするランク変換ユーティリティ
  - すべて標準ライブラリ + DuckDB に依存し、pandas 等には依存しない設計

- ニュースNLP / AI モジュール (kabusys.ai)
  - news_nlp:
    - calc_news_window: JST の前日 15:00 〜 当日 08:30 を UTC naive datetime に変換
    - score_news: raw_news / news_symbols を読み、銘柄ごとに記事を集約して OpenAI (gpt-4o-mini) にバッチ送信
      - バッチサイズ 20 銘柄、1 銘柄あたり最大 10 記事・最大 3000 文字でトリム
      - JSON Mode を利用して厳密な JSON を受け取る想定（レスポンスの前後余分テキスト復元処理あり）
      - 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ
      - レスポンス検証（results リスト・code の正規化・score の数値検証）、±1.0 にクリップ
      - 部分失敗時に既存スコアを消さないため、取得成功コードのみ DELETE → INSERT（冪等操作）
      - テスト時に _call_openai_api をパッチ可能（unittest.mock で差し替え）
      - API キー注入（api_key 引数 or OPENAI_API_KEY 環境変数）
  - regime_detector:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）判定
    - _calc_ma200_ratio, _fetch_macro_news, _score_macro を実装
      - マクロキーワード群に基づき raw_news からタイトル抽出（最大 20 記事）
      - OpenAI による JSON 出力のパースと再試行処理（リトライ・5xx 判定等）
      - API 失敗や構文エラー時は macro_sentiment=0.0 でフェイルセーフ
    - レジームスコアの合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - ルックアヘッドバイアス防止を意識した設計（datetime.today()/date.today() を直接参照しない、DB クエリは date < target_date）

- DuckDB 互換性・運用上の考慮
  - executemany に空リストを渡さないガードを追加（DuckDB 0.10 対応）
  - DuckDB の日付型取り扱いに対処するユーティリティ（_to_date）

- ロギングとデバッグ
  - 各処理で詳細な logger.debug / logger.info / logger.warning を追加し、障害時の解析性を向上

Security
- API キーやトークン（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）は必須設定とし、未設定時は ValueError を送出して明示的に失敗させる（誤動作防止）

Notes / 設計方針
- ルックアヘッドバイアス防止: すべての外部スコアやファクター計算は target_date を明示的に受け取り、内部で現在時刻を参照しない設計。
- フェイルセーフ原則: AI/API 呼び出しが失敗してもシステム全体が停止しないよう、適切なフォールバック（0.0 等）や部分書き込み保護を導入。
- モジュール分離: news_nlp と regime_detector で OpenAI 呼び出しのヘルパー実装を分離し、モジュール間で内部関数を共有しないことで結合度を下げる。

Changed
- 初版リリースのため変更履歴無し

Fixed
- 初版リリースのため修正履歴無し

Removed
- 初版リリースのため削除履歴無し

Deprecated
- 初版リリースのため非推奨事項無し

Security
- 重要な API トークン／パスワードは環境変数経由で管理することを想定（Settings クラスで必須化）

補足
- monitoring モジュールは __all__ に含まれているが、本リリースで提供される具体的実装ファイルは含まれていないため、今後追加予定。