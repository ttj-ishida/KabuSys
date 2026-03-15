# KabuSys — 日本株自動売買システム (README)

バージョン: 0.1.0

注意: 現在のリポジトリはパッケージ骨組み（スケルトン）です。各サブパッケージ（data, strategy, execution, monitoring）は名前空間として用意されています。実際の機能はこれから実装する前提の README です。

## プロジェクト概要
KabuSys は日本株の自動売買システムを構築するためのPythonパッケージ骨組みです。モジュールを分離して、
- 市場データ取得（data）
- 売買戦略（strategy）
- 注文実行（execution）
- システム監視・ログ（monitoring）

をそれぞれ実装・拡張できる設計になっています。

目的は、拡張しやすくテストしやすい自動売買フレームワークの基盤を提供することです。

## 機能一覧（想定）
現状は雛形のみですが、想定している機能は以下のとおりです。
- data
  - 市場データ（板情報、成行・指値、約定履歴、OHLC）の取得・キャッシュ
  - CSV/DBへの保存と読み込み
- strategy
  - 売買ロジック（シグナル生成）の実装ベース
  - パラメータ管理、バックテスト用インターフェース
- execution
  - 注文送受信（kabusAPI 等の接続ラッパー）
  - 発注、取消、注文状態追跡
- monitoring
  - ログ収集、稼働状況の可視化
  - アラート、パフォーマンス指標の出力

※ 各機能は今後の実装で追加します。README に示す使い方は想定インターフェース例を含みます。

## セットアップ手順

### 前提
- Python 3.8 以上を推奨
- git がインストールされていること

### 開発環境の準備（例）
1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージのインストール
   - 現在 requirements ファイルが無い場合は特になし。将来的には requirements.txt または pyproject.toml を追加してください。
   - 開発インストール（パッケージを編集しながら使う場合）
     ```
     pip install -e .
     ```
     ※ pip install -e . を使うには setup.py / pyproject.toml 等のパッケージメタデータが必要です。リポジトリにない場合は、開発中は `PYTHONPATH` に src を追加するか、モジュールを直接参照してください。

4. （任意）テストフレームワークの追加
   - pytest 等を用いる場合は開発依存に追加してください。

## 使い方（想定例）
現状のパッケージ構成からの基本的な使い方例を示します。

- パッケージ確認（バージョン表示）
```python
import kabusys
print(kabusys.__version__)  # "0.1.0"
```

- モジュールをインポートして雛形を作る
```python
from kabusys import data, strategy, execution, monitoring

# 例: strategy にクラスを実装して登録する（実際の Base クラスは未実装のため、以下は想定例）
class MyStrategy:
    def __init__(self, params):
        self.params = params

    def on_tick(self, tick):
        # tick データを受けて売買シグナルを返す
        return None

# 実際のフレームワークに組み込む場合は
# strategy.register(MyStrategy) などのAPIを実装して利用します（今後追加予定）
```

- 拡張の考え方（例）
  - data パッケージに `kabu_api.py` を追加して板情報取得を実装
  - strategy に `base.py` を作り、各戦略は `BaseStrategy` を継承
  - execution に実際の注文処理（APIキー管理、送信/取消）を実装
  - monitoring にログ集約・メトリクス出力（Prometheus や dashboard）を実装

README はあくまで骨子です。各パッケージの具体的なAPI設計は今後の実装で定めてください。

## ディレクトリ構成
現在のリポジトリに含まれる主要ファイル・ディレクトリ構成の例:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # バージョン・パッケージエクスポート
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
├─ README.md
└─ (その他: pyproject.toml / setup.cfg / requirements.txt などを追加可能)
```

将来的には各サブパッケージにモジュールファイル（例: data/kabu_api.py, strategy/base.py, execution/client.py, monitoring/logger.py）を追加していきます。

## 開発ガイド（簡易）
- ブランチ運用: main/master から機能ごとにブランチを切る
- テスト: pytest 等を導入してユニットテストを整備する
- ドキュメント: 各パッケージ内に docstring を書き、必要に応じて Sphinx 等でドキュメント化する

## 貢献
機能追加やバグ修正のプルリクエストは歓迎します。PR 作成時は以下を含めてください:
- 変更の目的
- 変更による影響範囲
- テスト（あれば）及び実行手順

## ライセンス
現状リポジトリにライセンスは追加されていません。公開する場合は適切なライセンス（例: MIT, Apache-2.0 等）を付与してください。

---

補足: この README は現状のパッケージ骨格に基づく設計ドキュメントです。実装が進むにつれて API 仕様やセットアップ手順を更新してください。必要であれば、各サブパッケージの推奨 API 仕様、ユースケース別のサンプル、CI/CD 設定例なども追記できます。