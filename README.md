# KabuSys

KabuSysは、日本株の自動売買システム用の最小構成パッケージ（スケルトン）です。データ取得、売買戦略（ストラテジ）、注文実行、モニタリングの4つの主要コンポーネントを想定したパッケージ構成を提供します。現在は骨組み（スキャフォールド）としての実装で、機能拡張や各種APIの統合を行いやすい設計になっています。

バージョン: 0.1.0

---

## 機能一覧

- パッケージ分割（モジュール分離）により、関心の分離を容易にする設計
  - data: 市場データの取得・加工用モジュール用スペース
  - strategy: 売買ロジック（ストラテジ）を実装するためのスペース
  - execution: 注文の発注・約定管理を行うためのスペース
  - monitoring: 稼働状況や取引の監視・ログ集約を行うためのスペース
- Pythonパッケージとしてインポート可能（開発者が機能を実装して拡張する前提）
- 軽量なスタートポイント（独自実装・外部API接続の追加が容易）

※現時点では実際のデータ取得や注文発注の実装は含まれていません。導入後に各モジュールを実装してください。

---

## セットアップ手順

前提
- Python 3.8 以降（プロジェクトに合わせて適宜読み替えてください）
- git

ローカルでの開発セットアップ例:

1. リポジトリをクローン
   - git clone <リポジトリのURL>
   - cd <リポジトリ>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. パッケージをインストール（開発モード）
   - pip install -e .

   ※依存パッケージがある場合は `requirements.txt` や `pyproject.toml` を用意して `pip install -r requirements.txt` のようにしてください（本スケルトンでは依存は含まれていません）。

4. （任意）環境変数などの設定
   - 実際の取引APIを利用する場合はAPIキーやシークレットを環境変数や設定ファイルにセットしてください。
     例:
     - KABU_API_KEY
     - KABU_API_SECRET
     - KABU_API_ENDPOINT

---

## 使い方

このパッケージは現状ではモジュールの配置（名前空間）を提供するのみです。以下は基本的なインポート例と、各モジュールに実装を追加して使う際のサンプル指針です。

- バージョン確認 / インポート例
```python
import kabusys
from kabusys import data, strategy, execution, monitoring

print(kabusys.__version__)  # "0.1.0"
```

- data モジュールの使い方（例: 市場データ取得）
  - src/kabusys/data 以下に `market.py` や `loader.py` を作り、データ取得の関数やクラスを実装します。
  - 例:
```python
# src/kabusys/data/market.py（例）
class MarketDataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_price(self, symbol: str):
        # 実装: API呼び出しやCSV読み込み等
        raise NotImplementedError
```

- strategy モジュールの使い方（例: 戦略実装）
  - src/kabusys/strategy に `base.py` を作成し、戦略の抽象クラスを定義して、個別戦略はそれを継承して実装します。
  - 例:
```python
# src/kabusys/strategy/base.py（例）
class BaseStrategy:
    def __init__(self, data_client):
        self.data_client = data_client

    def on_tick(self, tick):
        """
        ティックや定期呼び出し時に実行されるロジックをここに実装
        戻り値: 注文指示など
        """
        raise NotImplementedError
```

- execution モジュールの使い方（例: 注文実行）
  - src/kabusys/execution に `client.py` を作り、実際の注文送信・約定確認等の処理を実装します。
  - 例:
```python
# src/kabusys/execution/client.py（例）
class ExecutionClient:
    def __init__(self, api_key: str, secret: str):
        # 初期化
        pass

    def send_order(self, order):
        # 注文送信処理
        raise NotImplementedError
```

- monitoring モジュールの使い方（例: ログ、メトリクス、ダッシュボード）
  - src/kabusys/monitoring に `logger.py` / `metrics.py` 等を用意し、運用時の情報収集やアラート発火を実装します。

実運用の際は、data → strategy → execution の順に処理を繋ぎ、監視・ログは常時稼働させる設計が一般的です。

---

## ディレクトリ構成

現在のプロジェクト構成（主要ファイルを抜粋）:

- src/
  - kabusys/
    - __init__.py            # パッケージメタ情報（version, __all__等）
    - data/
      - __init__.py
      # データ取得関連のモジュールをここに追加（例: market.py, loader.py）
    - strategy/
      - __init__.py
      # 戦略の抽象クラスや個別戦略をここに追加（例: base.py, mean_reversion.py）
    - execution/
      - __init__.py
      # 注文実行クライアント等をここに追加（例: client.py）
    - monitoring/
      - __init__.py
      # ログやメトリクス用モジュールをここに追加（例: logger.py, metrics.py）

READMEやセットアップ関連ファイル（例: pyproject.toml, setup.cfg, requirements.txt）はプロジェクトルートに配置してください。

---

## 開発と拡張のヒント

- APIキーや接続情報はハードコードせず、環境変数や外部設定ファイルで管理してください。
- 重要処理（注文送信など）は例外処理・リトライやエラー時のロールバック設計を入れてください。
- テストはユニットテストと統合テストを分け、モックを利用して取引APIの呼び出しをシミュレートすることを推奨します。
- 本番環境では特にログ出力や監視を整備し、想定外の挙動にすぐ対応できるようにしましょう。

---

このリポジトリはスケルトン（雛形）です。必要な機能（データ取得、ストラテジー、注文APIとの接続、監視）を実装して、独自の自動売買システムを構築してください。質問や拡張の提案があればお知らせください。